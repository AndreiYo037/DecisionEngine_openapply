export default function CvDropzone({
  selectedFile,
  onFileSelect,
  isDragging,
  setIsDragging,
}) {
  const onDrop = (event) => {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file && file.type === 'application/pdf') {
      onFileSelect(file);
    }
  };

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={onDrop}
      className={`rounded-2xl border-2 border-dashed p-8 text-center transition ${
        isDragging
          ? 'border-slate-900 bg-slate-100'
          : 'border-slate-300 bg-white'
      }`}
    >
      <p className="text-base font-medium text-slate-900">
        Drag and drop your CV PDF
      </p>
      <p className="mt-1 text-sm text-slate-500">or choose a file manually</p>

      <label className="mt-4 inline-flex cursor-pointer rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100">
        Choose PDF
        <input
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) {
              onFileSelect(file);
            }
          }}
        />
      </label>

      {selectedFile ? (
        <p className="mt-3 text-sm text-slate-600">Selected: {selectedFile.name}</p>
      ) : null}
    </div>
  );
}
