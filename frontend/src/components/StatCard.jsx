export function StatCard({ label, value, hint, accent = 'signal' }) {
  const accents = {
    signal: 'from-signal-500/25 to-transparent text-signal-400',
    ember: 'from-ember-500/25 to-transparent text-ember-400',
    sun: 'from-sun-400/25 to-transparent text-sun-300',
  };

  return (
    <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-glow backdrop-blur-xl">
      <div className={`h-1.5 w-20 rounded-full bg-gradient-to-r ${accents[accent]}`} />
      <div className="mt-4 text-sm uppercase tracking-[0.25em] text-slate-400">{label}</div>
      <div className="mt-2 text-3xl font-semibold text-white">{value}</div>
      <div className="mt-2 text-sm text-slate-300">{hint}</div>
    </div>
  );
}
