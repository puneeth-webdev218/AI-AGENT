import { useEffect, useState } from 'react';
import { healthCheck, listDocuments, listResults } from '../lib/api';
import { SectionCard } from '../components/SectionCard';
import { StatCard } from '../components/StatCard';

export function Dashboard() {
  const [documents, setDocuments] = useState([]);
  const [results, setResults] = useState([]);
  const [health, setHealth] = useState('ok');
  const [error, setError] = useState('');

  useEffect(() => {
    let mounted = true;

    const runHealthCheck = () => {
      healthCheck()
        .then((healthPayload) => {
          if (!mounted) return;
          setHealth((healthPayload.status || 'ok').toLowerCase());
        })
        .catch((err) => {
          if (!mounted) return;
          setHealth('down');
          setError(err.message);
        });
    };

    runHealthCheck();
    const healthInterval = setInterval(runHealthCheck, 15000);

    listDocuments()
      .then((documentPayload) => {
        if (!mounted) return;
        setDocuments(documentPayload);
      })
      .catch((err) => {
        if (!mounted) return;
        setError((prev) => prev || err.message);
      });

    listResults()
      .then((resultPayload) => {
        if (!mounted) return;
        setResults(resultPayload);
      })
      .catch((err) => {
        if (!mounted) return;
        setError((prev) => prev || err.message);
      });

    return () => {
      mounted = false;
      clearInterval(healthInterval);
    };
  }, []);

  const healthLabel = health === 'ok' ? 'OK' : health;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="System status" value={healthLabel} hint="Backend health check and database connectivity." />
        <StatCard label="Documents" value={documents.length} hint="Uploaded or email-synced files tracked in the database." accent="sun" />
        <StatCard label="Results" value={results.length} hint="Structured extraction rows ready for analysis." accent="ember" />
      </div>

      {error ? <div className="rounded-2xl border border-ember-500/40 bg-ember-500/10 p-4 text-sm text-ember-400">{error}</div> : null}

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Latest documents" description="The newest processed files, including validation state and previews.">
          <Table
            headers={['File', 'Type', 'Status', 'Preview']}
            rows={documents.slice(0, 5).map((document) => [document.original_name, document.file_type, document.status, document.extracted_text_preview || '-'])}
          />
        </SectionCard>
        <SectionCard title="Latest results" description="Structured extraction rows stored in PostgreSQL.">
          <Table
            headers={['Name', 'USN', 'Subject', 'SGPA']}
            rows={results.slice(0, 5).map((result) => [result.student_name || '-', result.usn || '-', result.subject || '-', result.sgpa ?? '-'])}
          />
        </SectionCard>
      </div>
    </div>
  );
}

function Table({ headers, rows }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-white/10">
      <table className="min-w-full divide-y divide-white/10 text-sm">
        <thead className="bg-white/5 text-slate-300">
          <tr>
            {headers.map((header) => (
              <th key={header} className="px-4 py-3 text-left font-medium uppercase tracking-[0.2em]">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/10 bg-slate-950/40 text-slate-100">
          {rows.length === 0 ? (
            <tr>
              <td className="px-4 py-4 text-slate-400" colSpan={headers.length}>
                No data yet.
              </td>
            </tr>
          ) : (
            rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {row.map((cell, cellIndex) => (
                  <td key={cellIndex} className="max-w-[260px] px-4 py-3 align-top text-slate-200">
                    <span className="block truncate">{String(cell)}</span>
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
