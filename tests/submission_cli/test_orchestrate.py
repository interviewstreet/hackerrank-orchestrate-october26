"""Synthetic public-contract fixtures only; never execute participant solutions."""
import contextlib
import csv
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

SCRIPT = Path(__file__).resolve().parents[2] / 'orchestrate.py'
spec = importlib.util.spec_from_file_location('orchestrate', SCRIPT)
cli = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cli
spec.loader.exec_module(cli)

LOG = '''## [2026-11-20T10:00:00+05:30] SESSION START

tool=SyntheticHarness
model=synthetic-model

## [2026-11-20T10:01:00Z] Synthetic test turn

User Prompt (verbatim, secrets redacted):
Synthetic request: test the public format.
A second line with a colon: content.

Agent Response Summary:
Synthetic response for a grammar test only.

Actions:
* Created a synthetic fixture.

Context:
tool=SyntheticHarness
model=synthetic-model
'''


def step(operation='VERIFY_DATA_FLOW_DISABLED', state='DISABLED', phase='VERIFICATION', **kw):
    return dict(step_no=1, phase=phase, system_id='synthetic_system', resource_id='synthetic_resource',
                operation=operation, state=state, evidence_id='synthetic_evidence', **kw)


class Checkout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='synthetic-orchestrate-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.put('AGENTS.md', 'Synthetic test checkout\n')
        self.put('README.md', 'Synthetic setup instructions\n')
        self.put('code/main.any', 'Synthetic source; never executed\n')
        for report in cli.REPORTS[1:]:
            self.put(report, 'Synthetic report contents\n')
        self.put('dataset/deletion_requests.csv', 'case_id,email\nsynthetic_1,fake@example.invalid\nsynthetic_2,other@example.invalid\n')
        self.put('log.txt', LOG)
        self.output()

    def put(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if isinstance(value, bytes) else value.encode('utf-8'))
        return path

    def output(self, rows=None, header=cli.HEADERS, newline='\n', bom=False):
        stream = io.StringIO(newline='')
        writer = csv.writer(stream, lineterminator=newline)
        writer.writerow(header)
        writer.writerows(rows if rows is not None else [('synthetic_2', 'NOT_APPLICABLE', '[]'), ('synthetic_1', 'COMPLETE', json.dumps([step()]))])
        self.put('output.csv', ('\ufeff' if bom else '') + stream.getvalue())

    def checks(self):
        return cli.run_checks(self.root)

    def codes(self):
        return {f.code for f in self.checks().findings if f.severity == 'error'}

    def prepare(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return cli.prepare(self.root)

    def snapshot(self, directory=None):
        root = directory or self.root
        return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in root.rglob('*') if p.is_file()}

    def test_check_does_not_write(self):
        before = self.snapshot()
        self.assertFalse(self.codes())
        self.assertEqual(self.snapshot(), before)
        self.prepare()
        before = self.snapshot()
        self.checks()
        self.assertEqual(self.snapshot(), before)

    def test_success_repeated_fresh_zip_and_original_preservation(self):
        self.put('code/removed.any', 'old entry')
        before = self.snapshot()
        self.assertEqual(self.prepare(), 0)
        for path, data in before.items():
            self.assertEqual((self.root / path).read_bytes(), data[0])
            self.assertEqual((self.root / path).stat().st_mtime_ns, data[1])
        (self.root / 'code/removed.any').unlink()
        self.assertEqual(self.prepare(), 0)
        self.assertEqual({p.name for p in (self.root / 'submission').iterdir()}, cli.ARTIFACTS)
        with zipfile.ZipFile(self.root / 'submission/code.zip') as archive:
            self.assertEqual(archive.namelist(), sorted(['README.md', 'code/main.any', *cli.REPORTS[1:]]))
            self.assertIsNone(archive.testzip())
        self.assertEqual((self.root / 'submission/output.csv').read_bytes(), (self.root / 'output.csv').read_bytes())
        self.assertEqual((self.root / 'submission/log.txt').read_bytes(), (self.root / 'log.txt').read_bytes())
        self.assertFalse(list(self.root.glob('.orchestrate-backup-*')))

    def test_exclusions_and_custom_fixtures(self):
        for name in ['.git/config', 'dataset/private.csv', 'code/node_modules/x/file', 'code/nested/.venv/x',
                     'code/__pycache__/x.pyc', 'code/a/.env', 'code/.env.local', 'code/.aws/credentials',
                     'code/credentials.json', 'code/id_rsa', 'code/.DS_Store', 'code/._metadata', 'code/x.pyc']:
            self.put(name, 'not packaged')
        self.put('code/custom-environment/pyvenv.cfg', 'home=synthetic')
        self.put('code/custom-environment/installed', 'dependency')
        expected = ['code/requirements.txt', 'code/package-lock.json', 'code/.env.example', 'code/.env.sample',
                    'code/lib/source', 'code/bin/entry', 'code/dist/custom', 'code/evaluation/fixtures/dataset/file', 'code/spaces ü/file']
        for name in expected:
            self.put(name, 'legitimate fixture')
        self.prepare()
        with zipfile.ZipFile(self.root / 'submission/code.zip') as archive:
            self.assertEqual(set(archive.namelist()), set(['README.md', 'code/main.any', *cli.REPORTS[1:], *expected]))

    def test_archives_suffixes_and_signatures(self):
        for name, payload in [('x.ZIP', b'fake'), ('x.tar.gz', b'fake'), ('x.txt', b'PK\x03\x04data'),
                              ('x.txt', b'\x1f\x8bdata'), ('x.txt', b'7z\xbc\xaf\x27\x1cdata'), ('x.txt', b'Rar!data')]:
            with self.subTest(name=name, payload=payload):
                path = self.put('code/' + name, payload)
                self.assertIn('CODE_NESTED_ARCHIVE', self.codes())
                path.unlink()

    def test_missing_empty_and_legacy_reports(self):
        for path in ['README.md', *cli.REPORTS[1:]]:
            with self.subTest(path=path):
                original = (self.root / path).read_bytes()
                self.put(path, ' \n')
                self.assertIn('REPORT_MISSING', self.codes())
                (self.root / path).unlink()
                self.assertIn('REPORT_MISSING', self.codes())
                self.put(path, original)
        (self.root / cli.REPORTS[1]).unlink()
        self.put('evaluation/evaluation_report.md', 'legacy report')
        self.assertIn('REPORT_LOCATION', self.codes())
        shutil.rmtree(self.root / 'code')
        self.assertIn('CODE_EMPTY', self.codes())

    def test_case_collision_and_unsafe_name(self):
        # macOS can use a case-insensitive filesystem; exercise normalization directly via mocked traversal.
        original = list(Path.iterdir(self.root / 'code'))
        with mock.patch.object(Path, 'iterdir', autospec=True, side_effect=lambda p: iter(original + [next(p for p in original if p.is_file())]) if p == self.root / 'code' else iter([])):
            self.assertIn('CODE_UNSAFE_PATH', self.codes())
        if os.name != 'nt':
            self.put('code/unsafe:stream', 'unsafe Windows name')
            self.assertIn('CODE_UNSAFE_PATH', self.codes())

    def test_symlink_and_nonregular(self):
        path = self.root / 'code/link'
        try:
            path.symlink_to(self.root / 'README.md')
        except OSError:
            self.skipTest('Symlink creation requires OS privileges')
        self.assertIn('CODE_UNSAFE_PATH', self.codes())
        path.unlink()
        if hasattr(os, 'mkfifo'):
            os.mkfifo(path)
            self.assertIn('CODE_UNSAFE_PATH', self.codes())

    def test_symlinked_reference_parent(self):
        (self.root / 'dataset').rename(self.root / 'public-data')
        try:
            (self.root / 'dataset').symlink_to(self.root / 'public-data', target_is_directory=True)
        except OSError:
            self.skipTest('Symlink privilege unavailable')
        self.assertIn('REFERENCE_INVALID', self.codes())

    def test_reference_invalid_and_independent_errors(self):
        for payload in ['case_id\n', 'wrong\nx\n', 'case_id\nx\nx\n', 'case_id\n \n', 'case_id,email\nx\n']:
            with self.subTest(payload=payload):
                self.put('dataset/deletion_requests.csv', payload)
                result = self.checks()
                self.assertIsNone(result.expected_ids)
                self.assertIn('REFERENCE_INVALID', {f.code for f in result.findings})
        self.put('output.csv', b'\xff')
        self.put('log.txt', '')
        (self.root / cli.REPORTS[2]).unlink()
        self.assertTrue({'REFERENCE_INVALID', 'OUTPUT_UNREADABLE', 'TRANSCRIPT_UNREADABLE', 'REPORT_MISSING'} <= self.codes())

    def test_csv_bom_crlf_multiline_and_reverse_rows(self):
        s = step()
        s['evidence_id'] = 'synthetic\nmultiline'
        self.output([('synthetic_2', 'NOT_APPLICABLE', '[]'), ('synthetic_1', 'COMPLETE', json.dumps([s], indent=2))], newline='\r\n', bom=True)
        self.assertFalse(self.codes())
        original = (self.root / 'output.csv').read_bytes()
        self.prepare()
        self.assertEqual((self.root / 'submission/output.csv').read_bytes(), original)

    def test_csv_bad_headers_cells_quoting_and_binary(self):
        for value, code in [('case_id,case_id,steps_json\nx,x,[]\n', 'OUTPUT_HEADER'),
                            ('case_id,deletion_status,steps_json\nx,COMPLETE,[],extra\n', 'OUTPUT_CELLS'),
                            ('case_id,deletion_status,steps_json\nx,COMPLETE,"unterminated', 'OUTPUT_UNREADABLE'),
                            (b'PK\x03\x04binary', 'OUTPUT_UNREADABLE'), (b'\0', 'OUTPUT_UNREADABLE'),
                            ('case_id, deletion_status,steps_json\n', 'OUTPUT_HEADER')]:
            with self.subTest(value=value):
                self.put('output.csv', value)
                self.assertIn(code, self.codes())

    def test_id_and_status_checks(self):
        self.output([('unknown', 'bad', '[]'), ('unknown', 'COMPLETE', '[]'), (' ', 'COMPLETE', '[]')])
        self.assertTrue({'OUTPUT_UNKNOWN_IDS', 'OUTPUT_MISSING_IDS', 'OUTPUT_DUPLICATE_IDS', 'OUTPUT_BLANK_ID', 'OUTPUT_STATUS'} <= self.codes())

    def test_strict_json(self):
        for raw, code in [('{}', 'OUTPUT_JSON_ARRAY'), ('"[]"', 'OUTPUT_JSON_ARRAY'), ('[NaN]', 'OUTPUT_JSON'),
                          ('[Infinity]', 'OUTPUT_JSON'), ('[{"a":1,"a":2}]', 'OUTPUT_JSON'), ('[', 'OUTPUT_JSON')]:
            with self.subTest(raw=raw):
                self.output([('synthetic_1', 'COMPLETE', raw), ('synthetic_2', 'NOT_APPLICABLE', '[]')])
                self.assertIn(code, self.codes())

    def test_step_fields_types_numbering_operation(self):
        cases = []
        for key, val in [('step_no', True), ('system_id', 4), ('phase', None)]:
            s = step(); s[key] = val
            cases.append((s, 'OUTPUT_STEP_FIELDS'))
        s = step(); del s['state']; cases.append((s, 'OUTPUT_STEP_FIELDS'))
        s = step(); s['extra'] = ''; cases.append((s, 'OUTPUT_STEP_FIELDS'))
        s = step(); s['step_no'] = 2; cases.append((s, 'OUTPUT_STEP_NUMBER'))
        cases += [(step(state='INACTIVE'), 'OUTPUT_OPERATION'), (step(phase='FINDING'), 'OUTPUT_OPERATION')]
        for s, code in cases:
            with self.subTest(step=s):
                self.output([('synthetic_1', 'COMPLETE', json.dumps([s])), ('synthetic_2', 'NOT_APPLICABLE', '[]')])
                self.assertIn(code, self.codes())

    def test_step_order_status_phase(self):
        a = step(operation='DELETE_RECORD', state='ABSENT', phase='REMEDIATION')
        b = step(operation='REPORT_REMAINING_RECORD', state='PRESENT', phase='FINDING')
        b['step_no'] = 2
        self.output([('synthetic_1', 'COMPLETE', json.dumps([a, b])), ('synthetic_2', 'NOT_APPLICABLE', json.dumps([step()]))])
        self.assertTrue({'OUTPUT_STEP_ORDER', 'OUTPUT_COMPLETE_PHASE', 'OUTPUT_NOT_APPLICABLE'} <= self.codes())
        a, b = step(), step(); a['resource_id'] = 'z'; b['resource_id'] = 'a'; b['step_no'] = 2
        self.output([('synthetic_1', 'COMPLETE', json.dumps([a, b])), ('synthetic_2', 'NOT_APPLICABLE', '[]')])
        self.assertIn('OUTPUT_STEP_ORDER', self.codes())

    def test_log_invalid_cases(self):
        for value, code in [('', 'TRANSCRIPT_UNREADABLE'), (' \r\n', 'TRANSCRIPT_UNREADABLE'),
                            (b'PK\x03\x04archive', 'TRANSCRIPT_UNREADABLE'), (b'\xff', 'TRANSCRIPT_UNREADABLE'),
                            ('## [2026-11-20T10:00:00Z] SESSION START\nmodel=synthetic\n', 'TRANSCRIPT_SESSION_ONLY'),
                            ('requirements==1.0\n', 'TRANSCRIPT_FORMAT'),
                            ('```text\n' + LOG + '\n```', 'TRANSCRIPT_FORMAT'),
                            ('\n'.join('> ' + l for l in LOG.splitlines()), 'TRANSCRIPT_FORMAT'),
                            (LOG.replace('Synthetic response for a grammar test only.', ''), 'TRANSCRIPT_FORMAT')]:
            with self.subTest(value=value):
                self.put('log.txt', value)
                self.assertIn(code, self.codes())

    def test_code_only_prompt_body_and_quoted_format_inside_real_turn(self):
        prompt = 'Synthetic request: test the public format.\nA second line with a colon: content.'
        self.put('log.txt', LOG.replace(prompt, '```text\n' + LOG + '\n```'))
        self.assertFalse(self.codes())

    def test_log_valid_and_advisories(self):
        for log in [LOG, '\ufeff' + LOG.replace('\n', '\r\n'), LOG.replace('User Prompt (verbatim, secrets redacted):', 'User Prompt:')]:
            self.put('log.txt', log)
            self.assertFalse(self.codes())
        self.put('log.txt', LOG + '\n## [2026-11-20T11:00:00Z] Broken later turn\nUser Prompt:\ncontent\n')
        self.assertIn('TRANSCRIPT_INCOMPLETE', {f.code for f in self.checks().findings})
        self.put('log.txt', LOG.replace('model=synthetic-model', 'model=<exact_runtime_model_name>'))
        self.assertIn('TRANSCRIPT_METADATA', {f.code for f in self.checks().findings})
        self.put('log.txt', LOG.replace('Actions:', '**Actions:**'))
        self.assertIn('TRANSCRIPT_DECORATED', {f.code for f in self.checks().findings})

    def test_unknown_and_modified_submission_preserved(self):
        self.put('submission/unknown', 'participant file')
        before = self.snapshot()
        with self.assertRaises(cli.OperationalError): self.prepare()
        self.assertEqual(self.snapshot(), before)
        shutil.rmtree(self.root / 'submission')
        self.prepare()
        self.put('submission/log.txt', 'participant edit')
        with self.assertRaises(cli.OperationalError): self.prepare()
        self.assertEqual((self.root / 'submission/log.txt').read_text(), 'participant edit')

    def test_lock_exclusion_and_not_deleting_other_lock(self):
        with cli.preparation_lock(self.root):
            with self.assertRaises(cli.OperationalError): self.prepare()
            self.assertTrue((self.root / cli.LOCK).exists())
        self.assertFalse((self.root / cli.LOCK).exists())
        with cli.preparation_lock(self.root):
            self.put(cli.LOCK, 'another owner')
        self.assertEqual((self.root / cli.LOCK).read_text(), 'another owner')

    def test_staging_failure_preserves_prior_bundle(self):
        self.prepare()
        before = self.snapshot(self.root / 'submission')
        for target, exc in [('write_code_zip', OSError('synthetic disk full')), ('validate_staged_bundle', cli.OperationalError('synthetic bad ZIP'))]:
            with self.subTest(target=target), mock.patch.object(cli, target, side_effect=exc):
                with self.assertRaises((OSError, cli.OperationalError)): self.prepare()
                self.assertEqual(self.snapshot(self.root / 'submission'), before)
        self.assertFalse(list(self.root.glob('.orchestrate-stage-*')))

    def test_change_during_preparation(self):
        original = cli.validate_staged_bundle
        def change(stage, result):
            original(stage, result)
            self.put('code/main.any', 'changed while preparing')
        with mock.patch.object(cli, 'validate_staged_bundle', side_effect=change):
            with self.assertRaises(cli.OperationalError): self.prepare()
        self.assertFalse((self.root / 'submission').exists())

    def test_publication_failure_restores_old_bundle(self):
        self.prepare()
        previous = self.snapshot(self.root / 'submission')
        original = Path.rename
        def fail_stage(path, destination):
            if path.name.startswith('.orchestrate-stage-'):
                raise PermissionError('synthetic publication failure')
            return original(path, destination)
        with mock.patch.object(Path, 'rename', autospec=True, side_effect=fail_stage):
            with self.assertRaises(cli.OperationalError): self.prepare()
        self.assertEqual(self.snapshot(self.root / 'submission'), previous)
        self.assertEqual(self.prepare(), 0)

    def test_first_publication_failure_and_retry(self):
        with mock.patch.object(Path, 'rename', side_effect=PermissionError('synthetic')):
            with self.assertRaises(cli.OperationalError): self.prepare()
        self.assertFalse((self.root / cli.STATE).exists())
        self.assertEqual(self.prepare(), 0)

    def test_interrupt_between_renames_requires_recovery(self):
        self.prepare()
        before = self.snapshot(self.root / 'submission')
        original = Path.rename
        def interrupt(path, destination):
            if path.name.startswith('.orchestrate-stage-'):
                raise KeyboardInterrupt()
            return original(path, destination)
        with mock.patch.object(Path, 'rename', autospec=True, side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt): self.prepare()
        state = json.loads((self.root / cli.STATE).read_text())
        self.assertEqual(state['phase'], 'publishing')
        backup = self.root / state['backup']
        self.assertEqual(self.snapshot(backup), before)
        with self.assertRaisesRegex(cli.OperationalError, 'recovery'): self.prepare()
        # Explicit manual recovery of old bundle; CLI never guesses at crash state.
        backup.rename(self.root / 'submission')
        shutil.rmtree(self.root / state['stage'])
        cli.write_state(self.root, state['previous'])
        self.assertEqual(self.prepare(), 0)

    def test_stale_paths_refused(self):
        self.put('.orchestrate-stage-unknown/file', 'preserve me')
        with self.assertRaisesRegex(cli.OperationalError, 'Interrupted'): self.prepare()
        self.assertTrue((self.root / '.orchestrate-stage-unknown/file').exists())

    def test_size_limits_and_read_errors(self):
        with mock.patch.dict(cli.UPLOAD_LIMITS, {'code.zip': 1}):
            with self.assertRaisesRegex(cli.OperationalError, 'upload limit'): self.prepare()
        original = Path.read_bytes
        def unreadable(path):
            if path == self.root / 'output.csv': raise PermissionError('synthetic unreadable')
            return original(path)
        with mock.patch.object(Path, 'read_bytes', autospec=True, side_effect=unreadable):
            self.assertIn('OUTPUT_UNREADABLE', self.codes())

    def test_exit_codes_and_root_resolution_from_other_cwd(self):
        copied = self.put('orchestrate.py', SCRIPT.read_bytes())
        for args, expected in [(['check'], 0), (['prepare'], 0), (['unknown'], 2), (['--version'], 0)]:
            run = subprocess.run([sys.executable, '-B', str(copied), *args], cwd=self.root / 'code', capture_output=True)
            self.assertEqual(run.returncode, expected, run.stderr + run.stdout)
        self.put('output.csv', 'bad')
        run = subprocess.run([sys.executable, '-B', str(copied), 'prepare'], capture_output=True)
        self.assertEqual(run.returncode, 1)
        self.put(cli.LOCK, 'stale')
        run = subprocess.run([sys.executable, '-B', str(copied), 'prepare'], capture_output=True)
        self.assertEqual(run.returncode, 3)
        self.assertNotIn(b'Traceback', run.stderr)


    def test_portable_contract_fixtures(self):
        cases = json.loads(Path(__file__).with_name('contract_cases.json').read_text(encoding='utf-8'))
        for case in cases:
            with self.subTest(name=case['name']):
                self.output()
                self.put('log.txt', LOG)
                if 'csv' in case:
                    self.put('output.csv', case['csv'])
                if 'log' in case:
                    self.put('log.txt', case['log'])
                self.assertEqual(self.codes(), set(case['errors']))

    @unittest.skipUnless(os.name == 'nt', 'Windows junction behavior')
    def test_windows_junction_rejected(self):
        target = self.root / 'junction-target'
        target.mkdir()
        junction = self.root / 'code/junction'
        run = subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(target)], capture_output=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        try:
            self.assertIn('CODE_UNSAFE_PATH', self.codes())
        finally:
            junction.rmdir()

    def test_report_in_pruned_environment_is_not_packaged(self):
        self.put('code/evaluation/pyvenv.cfg', 'synthetic environment')
        self.assertIn('REPORT_NOT_PACKAGED', self.codes())
        self.assertEqual(self.prepare(), 1)

    def test_staged_corruption_is_revalidated(self):
        result = self.checks()
        stage = self.root / 'synthetic-stage'
        stage.mkdir()
        cli.write_code_zip(result.package_files, stage / 'code.zip', self.root, result)
        self.put('synthetic-stage/output.csv', 'invalid csv')
        self.put('synthetic-stage/log.txt', LOG)
        with self.assertRaisesRegex(cli.OperationalError, 'CSV/transcript'):
            cli.validate_staged_bundle(stage, result)
        self.put('synthetic-stage/output.csv', (self.root / 'output.csv').read_bytes())
        with zipfile.ZipFile(stage / 'code.zip', 'a') as archive:
            archive.writestr('unexpected', 'synthetic')
        with self.assertRaisesRegex(cli.OperationalError, 'ZIP verification'):
            cli.validate_staged_bundle(stage, result)

    def test_new_unknown_destination_during_prepare_is_preserved(self):
        original = cli.validate_staged_bundle
        def create_unknown(stage, result):
            original(stage, result)
            self.put('submission/custom', 'preserve this')
        with mock.patch.object(cli, 'validate_staged_bundle', side_effect=create_unknown):
            with self.assertRaisesRegex(cli.OperationalError, 'unknown submission'):
                self.prepare()
        self.assertEqual((self.root / 'submission/custom').read_text(), 'preserve this')

    def test_marker_failure_rolls_back_and_double_failure_preserves_recovery(self):
        self.prepare()
        previous = self.snapshot(self.root / 'submission')
        original_state = cli.write_state
        call_count = 0
        def fail_ready(root, state):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise OSError('synthetic marker failure')
            return original_state(root, state)
        with mock.patch.object(cli, 'write_state', side_effect=fail_ready):
            with self.assertRaises(cli.OperationalError): self.prepare()
        self.assertEqual(self.snapshot(self.root / 'submission'), previous)
        original_rename = Path.rename
        def double_failure(path, destination):
            if path.name.startswith(('.orchestrate-stage-', '.orchestrate-backup-')):
                raise OSError('synthetic publish and rollback failures')
            return original_rename(path, destination)
        with mock.patch.object(Path, 'rename', autospec=True, side_effect=double_failure):
            with self.assertRaisesRegex(cli.OperationalError, 'rollback failed'): self.prepare()
        state = json.loads((self.root / cli.STATE).read_text())
        self.assertEqual(state['phase'], 'publishing')
        self.assertEqual(self.snapshot(self.root / state['backup']), previous)
        self.assertTrue((self.root / state['stage']).is_dir())

    def test_actual_two_process_lock_contention(self):
        copied = self.put('orchestrate.py', SCRIPT.read_bytes())
        with cli.preparation_lock(self.root):
            run = subprocess.run([sys.executable, '-B', str(copied), 'prepare'], capture_output=True)
            self.assertEqual(run.returncode, 3)
            self.assertIn(b'lock exists', run.stderr)
            self.assertTrue((self.root / cli.LOCK).is_file())


if __name__ == '__main__':
    unittest.main()
