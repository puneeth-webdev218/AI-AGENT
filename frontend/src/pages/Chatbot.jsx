import { useEffect, useState } from 'react';
import { getLatestDocument, sendChatQuery } from '../lib/api';
import { SectionCard } from '../components/SectionCard';

export function Chatbot() {
  const [query, setQuery] = useState('Show the latest results with student name, USN, subject, and SGPA.');
  const [busy, setBusy] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState('');
  const [latestFile, setLatestFile] = useState(null);

  useEffect(() => {
    getLatestDocument()
      .then((payload) => setLatestFile(payload))
      .catch(() => setLatestFile(null));
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setResponse(null);
    try {
      const payload = await sendChatQuery(query);
      setResponse(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <SectionCard title="AI chatbot" description="Ask in natural language. The assistant answers from real extracted data via SQL-grounded retrieval.">
      {latestFile ? (
        <div className="mb-4 rounded-2xl border border-white/10 bg-slate-950/60 p-4 text-sm text-slate-200">
          <div className="text-xs uppercase tracking-[0.3em] text-slate-400">Latest analyzed file</div>
          <div className="mt-2"><span className="text-slate-400">File:</span> {latestFile.file_name}</div>
          <div><span className="text-slate-400">Records:</span> {latestFile.record_count}</div>
        </div>
      ) : null}
      <form className="space-y-4" onSubmit={handleSubmit}>
        <textarea
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          rows={5}
          className="w-full rounded-3xl border border-white/10 bg-slate-950/60 px-4 py-3 text-white outline-none transition focus:border-signal-500"
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-full bg-sun-400 px-5 py-3 font-medium text-slate-950 transition hover:bg-sun-300 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {busy ? 'Thinking...' : 'Ask chatbot'}
        </button>
      </form>

      {response ? (
        <div className="mt-5 space-y-4">
          <div className="rounded-2xl border border-sun-400/30 bg-sun-400/10 p-4">
            <div className="text-xs uppercase tracking-[0.3em] text-sun-300">Answer</div>
            <p className="mt-2 whitespace-pre-wrap text-sm text-slate-100">{response.answer}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
            <div className="text-xs uppercase tracking-[0.3em] text-slate-400">SQL</div>
            <pre className="mt-2 overflow-auto text-sm text-slate-100">{response.sql}</pre>
          </div>
          <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
            <div className="text-xs uppercase tracking-[0.3em] text-slate-400">Rows</div>
            <pre className="mt-2 overflow-auto text-sm text-slate-100">{JSON.stringify(response.rows, null, 2)}</pre>
          </div>
        </div>
      ) : null}
      {error ? <div className="mt-4 rounded-2xl border border-ember-500/40 bg-ember-500/10 p-4 text-sm text-ember-400">{error}</div> : null}
    </SectionCard>
  );
}
