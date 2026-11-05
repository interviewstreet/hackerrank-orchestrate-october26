"""Loopback presentation API and CSRF-protected case-specific Slack delivery.

Run: python code/server.py --dataset dataset
"""
from __future__ import annotations

import argparse
import csv
import hmac
import json
import os
import socket
import secrets
import threading
import time
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from advisor.envfile import load_env
from engine.case_analyzer import build_context
from engine.pipeline import run_cases
from notifications.slack import CASE_ID, SlackError, deliver, configuration
from presentation import present
from integrations.email.email_service import build_service_from_env
from integrations.email.http_adapter import EmailHttpAdapter, MAX_BODY, PREFIX
from integrations.email.operators import Operators

ORIGINS = {'http://127.0.0.1:5173', 'http://localhost:5173',
           'http://127.0.0.1:4173', 'http://localhost:4173'}


class ApiServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = os.name != 'nt'

    def server_bind(self):
        # Windows SO_REUSEADDR can route requests to an older server on the same port.
        if os.name == 'nt':
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def __init__(self, address, results, requests=()):
        if address[0] != '127.0.0.1':
            raise ValueError('This local API must bind to 127.0.0.1.')
        self.results = {r.case_id: r for r in results}
        self.requests = {r["case_id"]: r for r in requests}
        self.email = None
        self.sessions = {}
        self.lock = threading.Lock()
        self.delivery_lock = threading.Lock()
        self.sent = {}
        self.last_send = 0.0
        super().__init__(address, Handler)
        self.hosts = {urlsplit(o).netloc for o in ORIGINS} | {
            f'127.0.0.1:{self.server_port}', f'localhost:{self.server_port}'}


class Handler(BaseHTTPRequestHandler):
    server: ApiServer

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, format, *args):
        # URLs, exception strings and request bodies can contain identifiers or credentials.
        pass

    def reply(self, status, data, cookie=None):
        encoded = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        origin = self.headers.get('Origin')
        if origin in ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Access-Control-Allow-Credentials', 'true')
            self.send_header('Vary', 'Origin')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(encoded)

    def trusted_browser(self):
        return (self.headers.get('Host') in self.server.hosts
                and self.headers.get('Origin', '') in ORIGINS | {''}
                and self.headers.get('Sec-Fetch-Site') != 'cross-site')

    def session(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
            sid = cookie.get('erasight_session')
            with self.server.lock:
                item = self.server.sessions.get(sid.value if sid else '')
            return item if item and item['expires'] > time.monotonic() else None
        except (ValueError, KeyError, CookieError):
            return None

    def email_request(self):
        """Keep local-session/CSRF protections in front of the operator-authenticated adapter."""
        if not (self.path == PREFIX or self.path.startswith(PREFIX + '/')):
            return False
        session = self.session()
        if not self.trusted_browser() or self.headers.get('Origin', '') not in ORIGINS | {''} or not session:
            self.reply(403, {'error': 'Email session expired. Refresh and try again.'})
        elif self.command != 'GET' and not hmac.compare_digest(
                self.headers.get('X-CSRF-Token', '').encode(), session['csrf'].encode('ascii')):
            self.reply(403, {'error': 'Email session expired. Refresh and try again.'})
        else:
            try:
                size = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                size = -1
            if not 0 <= size <= MAX_BODY or self.headers.get('Transfer-Encoding'):
                self.reply(413, {'error': 'Request body is too large.'})
            elif self.server.email is None:
                self.reply(503, {'error': 'Email actions are not configured on the server.'})
            else:
                self.reply(*self.server.email.handle(self.command, self.path, self.headers, self.rfile.read(size)))
        return True

    def do_PUT(self):
        if not self.email_request():
            self.reply(404, {'error': 'Endpoint not found.'})

    def do_OPTIONS(self):
        if not self.trusted_browser() or self.headers.get('Origin') not in ORIGINS:
            return self.reply(403, {'error': 'Origin is not allowed.'})
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', self.headers['Origin'])
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-CSRF-Token, Authorization')
        self.send_header('Vary', 'Origin')
        self.end_headers()

    def do_GET(self):
        if self.email_request():
            return
        if not self.trusted_browser():
            return self.reply(403, {'error': 'This API is restricted to the local EraSight application.'})
        if self.path == '/api/session':
            now = time.monotonic()
            sid, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            with self.server.lock:
                self.server.sessions = {k: v for k, v in self.server.sessions.items() if v['expires'] > now}
                if len(self.server.sessions) >= 256:
                    return self.reply(429, {'error': 'Too many local sessions. Try again later.'})
                self.server.sessions[sid] = {'csrf': csrf, 'expires': now + 3600}
            try:
                configuration()
                configured = True
            except SlackError:
                configured = False
            return self.reply(200, {'csrf_token': csrf, 'slack_configured': configured, 'slack_report_format': 'html-v1'},
                              f'erasight_session={sid}; HttpOnly; SameSite=Strict; Path=/api; Max-Age=3600')
        if self.path == '/api/cases':
            return self.reply(200, [present(r, self.server.requests.get(r.case_id)) for r in self.server.results.values()])
        return self.reply(404, {'error': 'Endpoint not found.'})

    def do_POST(self):
        if self.email_request():
            return
        if not self.trusted_browser() or self.headers.get('Origin') not in ORIGINS:
            return self.reply(403, {'error': 'Notification request origin is not allowed.'})
        session = self.session()
        token = self.headers.get('X-CSRF-Token', '')
        if not session or not hmac.compare_digest(token.encode('utf-8'), session['csrf'].encode('ascii')):
            return self.reply(403, {'error': 'Notification session expired. Refresh and try again.'})
        parts = self.path.split('/')
        if len(parts) != 5 or parts[1:3] != ['api', 'cases'] or parts[4] != 'slack':
            return self.reply(404, {'error': 'Endpoint not found.'})
        case_id = parts[3]
        if not CASE_ID.fullmatch(case_id):
            return self.reply(400, {'error': 'Invalid case ID. Demo cases cannot be sent.'})
        result = self.server.results.get(case_id)
        if not result:
            return self.reply(404, {'error': 'Case not found. Refresh the engine results.'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if self.headers.get('Content-Type') != 'application/json' or not 0 <= size <= 64 or self.headers.get('Transfer-Encoding'):
                raise ValueError()
            if json.loads(self.rfile.read(size) or b'{}') != {}:
                raise ValueError()
        except (ValueError, UnicodeError):
            return self.reply(400, {'error': 'Send an empty JSON object; case results are loaded on the server.'})
        if not self.server.delivery_lock.acquire(blocking=False):
            return self.reply(409, {'error': 'A Slack notification is already being sent. Please wait.'})
        try:
            now = time.monotonic()
            if now - self.server.sent.get(case_id, -1000) < 30:
                return self.reply(409, {'error': 'This case was just sent to Slack. Wait before sending again.'})
            if now - self.server.last_send < 1:
                return self.reply(429, {'error': 'Please wait a moment before sending another Slack notification.'})
            try:
                deliver(result)
            except SlackError as error:
                return self.reply(error.status, {'error': str(error)})
            except Exception:
                return self.reply(502, {'error': 'Slack delivery could not be confirmed. Check the channel before retrying.'})
            self.server.sent[case_id] = self.server.last_send = time.monotonic()
            return self.reply(200, {'status': 'sent', 'case_id': case_id})
        finally:
            self.server.delivery_lock.release()


def load_results(dataset):
    context = build_context(dataset)
    if any(status != 'PROCESSED' for status in context.store.status.values()):
        raise RuntimeError('Evidence processing is incomplete. Install pdftotext/tesseract and check the dataset before sending alerts.')
    return run_cases(context.ctx.requests, context)


def main():
    root = Path(__file__).resolve().parents[1]
    load_env(root / '.env')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=root / 'dataset')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    try:
    results = load_results(args.dataset)
    with (args.dataset / 'deletion_requests.csv').open(encoding='utf-8', newline='') as request_file:
    requests = list(csv.DictReader(request_file))
    with ApiServer(('127.0.0.1', args.port), results, requests) as server:
    server.email = EmailHttpAdapter(
        build_service_from_env(), Operators.from_env(os.environ),
        case_provider=lambda cid: server.results[cid].to_dict() if cid in server.results else None)
    print(f'EraSight local API: http://127.0.0.1:{args.port} ({len(results)} engine cases)')
    server.serve_forever()
    except KeyboardInterrupt:
    pass
    except Exception:
    raise SystemExit('Unable to start the local API. Check the dataset, required parser tools and port. No credentials were logged.') from None


if __name__ == '__main__':
    main()
