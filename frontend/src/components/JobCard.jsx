export default function JobCard({ opportunity, onOpenMessage }) {
  const { job, best_contact: bestContact } = opportunity;

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-slate-500">{job.company}</p>
          <h3 className="text-xl font-semibold text-slate-900">{job.title}</h3>
        </div>
        <div className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700">
          Match Score: {job.match_score}%
        </div>
      </div>

      <div className="rounded-xl bg-amber-50 p-4">
        <p className="text-sm font-semibold text-amber-700">Best Contact</p>
        <p className="mt-1 text-base font-bold text-slate-900">{bestContact.name}</p>
        <p className="text-sm text-slate-600">{bestContact.role}</p>
        <p className="mt-2 inline-block rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
          High confidence
        </p>
        <p className="mt-3 text-sm text-slate-700">
          <span className="font-semibold">Why this person:</span> {bestContact.reason}
        </p>
      </div>

      <button
        type="button"
        onClick={onOpenMessage}
        className="mt-4 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
      >
        View Outreach Message
      </button>
    </article>
  );
}
