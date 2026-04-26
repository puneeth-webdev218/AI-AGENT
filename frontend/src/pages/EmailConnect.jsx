import { useEffect, useMemo, useState } from 'react';
import {
  analyzeResultEmail,
  beginGmailOAuth,
  fetchGmailEmails,
  fetchResultEmails,
  getGmailConnectionStatus,
  processEmailById,
} from '../lib/api';
import { SectionCard } from '../components/SectionCard';

export function EmailConnect() {
  const [connecting, setConnecting] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Checking Gmail connection...');
  const [connectionState, setConnectionState] = useState('idle');
  const [emails, setEmails] = useState([]);
  const [nextPageToken, setNextPageToken] = useState(null);
  const [resultEmails, setResultEmails] = useState([]);
  const [checkingResults, setCheckingResults] = useState(false);
  const [analyzingId, setAnalyzingId] = useState('');
  const [processingEmailId, setProcessingEmailId] = useState('');
  const [error, setError] = useState('');
  const [maxResults, setMaxResults] = useState(10);
  const queryParams = useMemo(() => new URLSearchParams(window.location.search), []);

  async function checkConnection() {
    try {
      const payload = await getGmailConnectionStatus();
      if (payload.connected) {
        setConnectionState('success');
        setStatusMessage('Connected to Gmail via OAuth2.');
      } else {
        setConnectionState('idle');
        setStatusMessage('Not connected. Click Connect Gmail to start OAuth2.');
      }
    } catch (err) {
      setConnectionState('failed');
      setStatusMessage('Failed to check Gmail connection state.');
      setError(err.message || 'Connection status check failed');
    }
  }

  useEffect(() => {
    if (queryParams.get('gmail_connected') === 'true') {
      setStatusMessage('Gmail connected successfully. Fetching latest emails...');
    }
    checkConnection();
  }, [queryParams]);

  useEffect(() => {
    if (queryParams.get('gmail_connected') === 'true') {
      loadEmails(undefined);
    }
  }, [queryParams]);

  function handleConnect() {
    setConnecting(true);
    setError('');
    setStatusMessage('Redirecting to Google OAuth consent screen...');
    setConnectionState('checking');
    beginGmailOAuth(`${window.location.origin}/email`);
  }

  async function loadEmails(pageToken) {
    setFetching(true);
    setError('');
    try {
      const payload = await fetchGmailEmails({ maxResults, pageToken });
      setEmails(payload.emails || []);
      setNextPageToken(payload.nextPageToken || null);
      setConnectionState('success');
      setStatusMessage((payload.count || 0) > 0 ? `Fetched ${payload.count} emails.` : (payload.message || 'No emails found.'));
    } catch (err) {
      setConnectionState('failed');
      setError(err.message || 'Failed to fetch emails');
      setStatusMessage('Failed to fetch emails.');
    } finally {
      setFetching(false);
    }
  }

  async function checkEmailsForResults() {
    setCheckingResults(true);
    setError('');
    try {
      const payload = await fetchResultEmails({ maxResults });
      setResultEmails(payload.emails || []);
      setStatusMessage(
        (payload.count || 0) > 0
          ? `Result emails found: ${payload.count}`
          : (payload.message || 'No result emails found.'),
      );
    } catch (err) {
      setError(err.message || 'Failed to check result emails');
      setStatusMessage('Failed to check emails for results.');
    } finally {
      setCheckingResults(false);
    }
  }

  async function analyzeEmail(messageId) {
    setAnalyzingId(messageId);
    setError('');
    try {
      const payload = await analyzeResultEmail(messageId);
      const count = payload.analyses?.length || 0;
      setStatusMessage(count > 0 ? `Analyzed ${count} PDF attachment(s) from selected email.` : 'Analysis completed.');
    } catch (err) {
      setError(err.message || 'Failed to analyze selected email');
      setStatusMessage('Email analysis failed.');
    } finally {
      setAnalyzingId('');
    }
  }

  async function processSelectedEmail(emailId) {
    if (!emailId) {
      setError('Selected email has no id.');
      return;
    }
    setProcessingEmailId(emailId);
    setError('');
    try {
      const payload = await processEmailById(emailId);
      const inserted = payload.records_inserted ?? 0;
      setStatusMessage(`Email attachment processed. Records inserted: ${inserted}`);
    } catch (err) {
      setError(err.message || 'Failed to process selected email attachment');
      setStatusMessage('Email processing failed.');
    } finally {
      setProcessingEmailId('');
    }
  }

  return (
    <SectionCard title="Email integration" description="Connect Gmail securely with OAuth2 and fetch inbox emails directly.">
      <div className="grid gap-4 md:grid-cols-3">
        <button
          type="button"
          onClick={handleConnect}
          disabled={connecting || fetching}
          className="rounded-full bg-signal-500 px-5 py-3 font-medium text-slate-950 transition hover:bg-signal-400 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {connecting ? 'Redirecting...' : 'Connect Gmail'}
        </button>
        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-300" htmlFor="maxResults">Emails:</label>
          <input
            id="maxResults"
            type="number"
            min={1}
            max={50}
            value={maxResults}
            onChange={(event) => setMaxResults(Math.min(50, Math.max(1, Number(event.target.value) || 10)))}
            className="w-24 rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2 text-white"
          />
        </div>
        <button
          type="button"
          onClick={() => loadEmails(undefined)}
          disabled={fetching}
          className="rounded-full border border-white/20 px-5 py-3 text-slate-100 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {fetching ? 'Fetching...' : 'Fetch Emails'}
        </button>
      </div>
      <div className="mt-4">
        <button
          type="button"
          onClick={checkEmailsForResults}
          disabled={checkingResults || fetching}
          className="rounded-full bg-sun-400 px-5 py-3 font-medium text-slate-950 transition hover:bg-sun-300 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {checkingResults ? 'Checking...' : 'Check Emails for Results'}
        </button>
      </div>
      {statusMessage ? <div className="mt-4 rounded-2xl border border-white/10 bg-slate-950/40 p-3 text-sm text-slate-300">{statusMessage}</div> : null}
      {error ? <div className="mt-4 rounded-2xl border border-red-500/30 bg-red-950/40 p-3 text-sm text-red-200"><strong>Error:</strong> {error}</div> : null}
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className={`rounded-2xl border p-4 text-sm text-slate-200 ${
          connectionState === 'success' ? 'border-green-500/50 bg-green-950/30' :
          connectionState === 'failed' ? 'border-red-500/50 bg-red-950/30' :
          connectionState === 'checking' ? 'border-blue-500/50 bg-blue-950/30' :
          'border-white/10 bg-slate-950/50'
        }`}>
          <div className="text-slate-400 text-xs">Connection status</div>
          <div className="mt-2 text-lg font-semibold">
            {connectionState === 'success'
              ? '✅ Connected'
              : connectionState === 'failed'
                ? '❌ Failed'
                : connectionState === 'checking'
                  ? '🔄 Checking...'
                  : '⏳ Not connected yet'}
          </div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4 text-sm text-slate-200">
          <div className="text-slate-400 text-xs">Fetched emails</div>
          <div className="mt-2 text-lg font-semibold">{emails.length}</div>
        </div>
      </div>
      {emails.length > 0 ? (
        <div className="mt-4 space-y-2 rounded-2xl border border-white/10 bg-slate-950/60 p-4 text-sm text-slate-100">
          <div className="text-xs uppercase tracking-[0.3em] text-slate-400">Fetched email list</div>
          <div className="max-h-72 overflow-auto space-y-2">
            {emails.map((emailItem) => (
              <div key={emailItem.id} className="rounded-xl border border-white/10 bg-white/5 p-3">
                <div className="font-medium text-white">{emailItem.subject || '-'}</div>
                <div className="text-xs text-slate-300">From: {emailItem.from || '-'}</div>
                <div className="text-xs text-slate-300">Date: {emailItem.date || '-'}</div>
                <div className="mt-2 text-xs text-slate-300">Snippet: {emailItem.snippet || '-'}</div>
                <button
                  type="button"
                  onClick={() => processSelectedEmail(emailItem.id || emailItem.messageId)}
                  disabled={Boolean(processingEmailId)}
                  className="mt-3 rounded-full border border-signal-300/60 px-3 py-1 text-xs text-signal-200 hover:bg-signal-300/20 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {processingEmailId === (emailItem.id || emailItem.messageId) ? 'Processing...' : 'Analyze / Process'}
                </button>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      {resultEmails.length > 0 ? (
        <div className="mt-4 space-y-2 rounded-2xl border border-sun-400/30 bg-sun-400/10 p-4 text-sm text-slate-100">
          <div className="text-xs uppercase tracking-[0.3em] text-sun-300">Result email candidates</div>
          <div className="max-h-80 overflow-auto space-y-2">
            {resultEmails.map((emailItem) => (
              <div key={emailItem.messageId} className="rounded-xl border border-white/10 bg-white/5 p-3">
                <div className="font-medium text-white">{emailItem.subject || '-'}</div>
                <div className="text-xs text-slate-300">From: {emailItem.from || '-'}</div>
                <div className="text-xs text-slate-300">Date: {emailItem.date || '-'}</div>
                <div className="mt-1 text-xs text-sun-300">Result Email Found</div>
                <button
                  type="button"
                  onClick={() => analyzeEmail(emailItem.messageId)}
                  disabled={Boolean(analyzingId)}
                  className="mt-3 rounded-full border border-sun-300/60 px-3 py-1 text-xs text-sun-200 hover:bg-sun-300/20 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {analyzingId === emailItem.messageId ? 'Analyzing...' : 'Analyze'}
                </button>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      <div className="mt-4 flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-200">Pagination</h3>
        <button type="button" onClick={checkConnection} className="rounded-full border border-white/20 px-3 py-1 text-xs text-slate-200 hover:bg-white/10">
          Refresh connection state
        </button>
      </div>
      <div className="mt-2 rounded-2xl border border-white/10 bg-slate-950/50 p-3 text-xs text-slate-200">
        <div><span className="text-slate-400">Next page token:</span> {nextPageToken || 'None'}</div>
        <button
          type="button"
          onClick={() => loadEmails(nextPageToken)}
          disabled={!nextPageToken || fetching}
          className="mt-3 rounded-full border border-white/20 px-3 py-1 text-xs text-slate-200 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
        >
          Load next page
        </button>
      </div>
      {error ? <div className="mt-4 rounded-2xl border border-ember-500/40 bg-ember-500/10 p-4 text-sm text-ember-400">{error}</div> : null}
    </SectionCard>
  );
}
