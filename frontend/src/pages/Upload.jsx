import { useState } from 'react';
import { uploadDocument } from '../lib/api';
import { SectionCard } from '../components/SectionCard';

export function Upload() {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  async function handleSubmit(event) {
    event.preventDefault();
    if (!file) {
      setError('Choose a file before uploading.');
      return;
    }
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const payload = await uploadDocument(file);
      setMessage(`Processed document #${payload.document.id} with status ${payload.document.status}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <SectionCard title="Manual upload" description="Upload PDF, image, or Excel files for strict extraction and validation.">
      <form className="space-y-4" onSubmit={handleSubmit}>
        <label className="block rounded-3xl border border-dashed border-white/20 bg-slate-950/40 p-6 text-center">
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.xls,.xlsx"
            className="hidden"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
          <div className="text-sm text-slate-300">Click to choose a document</div>
          <div className="mt-2 text-lg font-medium text-white">{file ? file.name : 'No file selected'}</div>
        </label>
        <button
          type="submit"
          disabled={busy}
          className="rounded-full bg-signal-500 px-5 py-3 font-medium text-slate-950 transition hover:bg-signal-400 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {busy ? 'Processing...' : 'Upload and process'}
        </button>
      </form>
      {message ? <div className="mt-4 rounded-2xl border border-signal-500/40 bg-signal-500/10 p-4 text-sm text-signal-400">{message}</div> : null}
      {error ? <div className="mt-4 rounded-2xl border border-ember-500/40 bg-ember-500/10 p-4 text-sm text-ember-400">{error}</div> : null}
    </SectionCard>
  );
}
