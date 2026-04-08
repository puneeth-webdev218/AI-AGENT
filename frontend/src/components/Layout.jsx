import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/upload', label: 'Upload' },
  { to: '/email', label: 'Email Connect' },
  { to: '/chat', label: 'Chatbot' },
];

export function Layout({ children }) {
  return (
    <div className="min-h-screen text-slate-100">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-4 lg:px-8">
        <header className="mb-6 rounded-3xl border border-white/10 bg-white/5 px-5 py-4 shadow-glow backdrop-blur-xl">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-signal-400">Academic Intelligence</p>
              <h1 className="mt-2 text-2xl font-semibold text-white">Automated Result Extraction and Analysis Agent</h1>
              <p className="mt-1 max-w-3xl text-sm text-slate-300">
                Upload academic documents, sync mailboxes, extract only verified fields, and query real database results safely.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs text-slate-300 sm:grid-cols-4">
              <Badge label="PDF OCR" value="Strict" />
              <Badge label="SQL mode" value="SELECT only" />
              <Badge label="Storage" value="PostgreSQL" />
              <Badge label="Sync" value="IMAP + cron" />
            </div>
          </div>
          <nav className="mt-5 flex flex-wrap gap-2">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  [
                    'rounded-full px-4 py-2 text-sm transition',
                    isActive
                      ? 'bg-signal-500 text-slate-950 shadow-lg shadow-signal-500/20'
                      : 'border border-white/10 bg-white/5 text-slate-200 hover:bg-white/10',
                  ].join(' ')
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </header>
        <main className="flex-1">{children}</main>
      </div>
    </div>
  );
}

function Badge({ label, value }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-ink-900/70 px-3 py-2">
      <div className="text-[10px] uppercase tracking-[0.3em] text-slate-400">{label}</div>
      <div className="mt-1 text-sm font-medium text-white">{value}</div>
    </div>
  );
}
