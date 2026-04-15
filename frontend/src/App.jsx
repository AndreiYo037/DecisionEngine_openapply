import { useMemo, useState } from 'react';
import CvDropzone from './components/CvDropzone';
import JobCard from './components/JobCard';
import MessageModal from './components/MessageModal';

const API_BASE = 'http://127.0.0.1:8000';

function App() {
  const [stage, setStage] = useState('landing');
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [opportunities, setOpportunities] = useState([]);
  const [rolePreference, setRolePreference] = useState('all');
  const [industryPreference, setIndustryPreference] = useState('all');
  const [activeOpportunity, setActiveOpportunity] = useState(null);

  const filteredOpportunities = useMemo(() => {
    return opportunities.filter((item) => {
      const roleText = item.job.title.toLowerCase();
      const companyText = item.job.company.toLowerCase();

      const roleMatch =
        rolePreference === 'all' ||
        (rolePreference === 'data' && roleText.includes('data')) ||
        (rolePreference === 'swe' &&
          (roleText.includes('software') || roleText.includes('engineer'))) ||
        (rolePreference === 'marketing' && roleText.includes('marketing'));

      const industryMatch =
        industryPreference === 'all' || companyText.includes(industryPreference);

      return roleMatch && industryMatch;
    });
  }, [opportunities, rolePreference, industryPreference]);

  const onAnalyze = async () => {
    if (!selectedFile) {
      setError('Please upload a PDF CV first.');
      return;
    }

    setError('');
    setLoading(true);
    setStage('upload');

    try {
      const formData = new FormData();
      formData.append('cv_file', selectedFile);
      formData.append('include_ingestion', 'true');

      const response = await fetch(`${API_BASE}/match_jobs_from_cv`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || 'Request failed');
      }

      const payload = await response.json();
      setOpportunities(payload.opportunities || []);
      setStage('results');
    } catch (requestError) {
      setError(requestError.message || 'Something went wrong.');
      setStage('upload');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen px-4 py-10 md:px-8">
      <div className="mx-auto max-w-4xl">
        {stage === 'landing' ? (
          <section className="rounded-3xl bg-white p-10 shadow-sm">
            <h1 className="text-4xl font-semibold tracking-tight text-slate-900">
              Find internships you can actually get - and who to contact
            </h1>
            <p className="mt-4 max-w-2xl text-slate-600">
              Upload your CV. We will show you only high-probability opportunities
              and exactly how to reach out.
            </p>
            <button
              type="button"
              onClick={() => setStage('upload')}
              className="mt-8 rounded-xl bg-slate-900 px-5 py-3 font-medium text-white hover:bg-slate-800"
            >
              Upload CV
            </button>
          </section>
        ) : null}

        {stage === 'upload' ? (
          <section className="rounded-3xl bg-white p-8 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-900">Upload your CV</h2>
            <p className="mt-2 text-slate-600">
              We will find only opportunities you can act on immediately.
            </p>

            <div className="mt-6">
              <CvDropzone
                selectedFile={selectedFile}
                onFileSelect={setSelectedFile}
                isDragging={isDragging}
                setIsDragging={setIsDragging}
              />
            </div>

            {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}

            <div className="mt-6 flex gap-3">
              <button
                type="button"
                onClick={onAnalyze}
                disabled={loading}
                className="rounded-xl bg-slate-900 px-5 py-3 font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
              >
                {loading
                  ? 'Analyzing your profile and matching opportunities...'
                  : 'Analyze CV'}
              </button>
              <button
                type="button"
                onClick={() => setStage('landing')}
                className="rounded-xl border border-slate-300 px-5 py-3 font-medium text-slate-700 hover:bg-slate-100"
              >
                Back
              </button>
            </div>
          </section>
        ) : null}

        {stage === 'results' ? (
          <section>
            <div className="mb-6 rounded-2xl bg-white p-4 shadow-sm md:flex md:items-center md:justify-between">
              <div>
                <h2 className="text-2xl font-semibold text-slate-900">Actionable Opportunities</h2>
                <p className="text-sm text-slate-600">
                  Focused results only: high fit and high-confidence contacts.
                </p>
              </div>
              <div className="mt-4 flex flex-wrap gap-2 md:mt-0">
                <select
                  value={rolePreference}
                  onChange={(event) => setRolePreference(event.target.value)}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="all">All roles</option>
                  <option value="data">Data</option>
                  <option value="swe">SWE</option>
                  <option value="marketing">Marketing</option>
                </select>
                <select
                  value={industryPreference}
                  onChange={(event) => setIndustryPreference(event.target.value)}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="all">All industries</option>
                  <option value="fintech">Fintech</option>
                  <option value="e-commerce">E-commerce</option>
                </select>
              </div>
            </div>

            {filteredOpportunities.length === 0 ? (
              <div className="rounded-2xl bg-white p-8 text-center shadow-sm">
                <p className="text-lg font-medium text-slate-900">
                  No high-probability opportunities found.
                </p>
                <p className="mt-2 text-slate-600">
                  Try adjusting your preferences or CV.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredOpportunities.map((item, index) => (
                  <JobCard
                    key={`${item.job.company}-${item.job.title}-${index}`}
                    opportunity={item}
                    onOpenMessage={() => setActiveOpportunity(item)}
                  />
                ))}
              </div>
            )}
          </section>
        ) : null}
      </div>

      <MessageModal
        isOpen={Boolean(activeOpportunity)}
        onClose={() => setActiveOpportunity(null)}
        message={activeOpportunity?.message}
        company={activeOpportunity?.job.company}
        contactName={activeOpportunity?.best_contact.name}
      />
    </main>
  );
}

export default App;
