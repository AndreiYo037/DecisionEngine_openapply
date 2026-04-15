export default function MessageModal({
  isOpen,
  onClose,
  message,
  company,
  contactName,
}) {
  if (!isOpen) {
    return null;
  }

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(message || '');
    } catch {
      // Ignore clipboard errors silently for compatibility.
    }
  };

  const linkedInSearchUrl = `https://www.google.com/search?q=${encodeURIComponent(
    `site:linkedin.com ${contactName} ${company}`
  )}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
      <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-2xl">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h3 className="text-xl font-semibold text-slate-900">Outreach Message</h3>
            <p className="text-sm text-slate-500">
              Edit it before sending if needed.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-2 py-1 text-slate-500 hover:bg-slate-100 hover:text-slate-700"
          >
            Close
          </button>
        </div>

        <textarea
          className="h-52 w-full rounded-xl border border-slate-200 p-3 text-sm leading-6 outline-none focus:border-slate-400"
          defaultValue={message}
        />

        <div className="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={onCopy}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          >
            Copy message
          </button>
          <a
            href={linkedInSearchUrl}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
          >
            Open LinkedIn search
          </a>
        </div>
      </div>
    </div>
  );
}
