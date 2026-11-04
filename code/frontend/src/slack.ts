/** Slack requests carry only a case ID; the backend owns message content and secrets. */
async function slackRequest(base: string, path: string, options: RequestInit = {}) {
  let response: Response;
  try {
    response = await fetch(`${base}${path}`, { ...options, credentials: 'include', signal: AbortSignal.timeout(15000) });
  } catch {
    throw new Error('Slack delivery could not be confirmed. Check the channel and that the local API is running before retrying.');
  }
  let data;
  try { data = await response.json(); } catch { throw new Error('The Slack API returned an invalid response. Check that the local API is running.'); }
  if (!response.ok) {
    // Only map known server outcomes; never display arbitrary proxy/upstream error bodies.
    const errors: Record<number, string> = {
      400: 'Invalid case. Demo cases cannot be sent.', 403: 'Slack session expired or origin rejected. Refresh and try again.',
      404: 'Case not found. Refresh the engine results.', 409: 'This case was just sent, or another send is in progress. Please wait.',
      429: 'Slack rate limit reached. Wait before trying again.',
      503: 'Slack is not configured. Set SLACK_WEBHOOK_URL on the server.',
    };
    throw new Error(errors[response.status] || 'Slack delivery could not be confirmed. Check the channel before retrying.');
  }
  return data;
}
export async function getSlackSession(base: string) {
  const data = await slackRequest(base, '/api/session');
  if (!data || typeof data.csrf_token !== 'string' || typeof data.slack_configured !== 'boolean') throw new Error('The Slack API returned an invalid session.');
  if (data.slack_report_format !== 'html-v1') throw new Error('This API does not support HTML Slack reports. Restart the EraSight backend and refresh this page.');
  return data as { csrf_token: string; slack_configured: boolean };
}
export async function sendSlackReport(base: string, caseId: string) {
  if (!/^(?:case|sample(?:_case)?|mini)_\d{1,12}$/.test(caseId)) throw new Error('Demo cases cannot be sent. Switch to live engine results first.');
  const session = await getSlackSession(base);
  if (!session.slack_configured) throw new Error('Slack is not configured. Set SLACK_WEBHOOK_URL on the server.');
  const data = await slackRequest(base, `/api/cases/${encodeURIComponent(caseId)}/slack`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': session.csrf_token }, body: '{}',
  });
  if (!data || data.status !== 'sent' || data.case_id !== caseId) throw new Error('Slack delivery could not be confirmed. Check the channel before retrying.');
}
