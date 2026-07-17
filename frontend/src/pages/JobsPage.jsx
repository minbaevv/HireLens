import { useEffect, useState } from 'react'
import api from '../api/client'
import { Plus, Copy, Check, Trash2, ToggleLeft, ToggleRight, Briefcase } from 'lucide-react'
import Spinner from '../components/Spinner'
import { useT } from '../i18n'

const WEIGHT_PROFILES = {
  technical: { technical: 45, experience: 30, soft: 15, motivation: 10 },
  management: { soft: 35, experience: 30, motivation: 20, technical: 15 },
}
const DEFAULT_CUSTOM_WEIGHTS = { technical: 25, soft: 25, experience: 25, motivation: 25 }
const WEIGHT_KEYS = ['technical', 'soft', 'experience', 'motivation']

function matchWeightProfile(w) {
  if (!w) return 'balanced'
  for (const [name, preset] of Object.entries(WEIGHT_PROFILES)) {
    if (WEIGHT_KEYS.every(k => (preset[k] ?? 0) === (w[k] ?? 0))) return name
  }
  return 'custom'
}

function JobModal({ job, onClose, onSaved }) {
  const { t } = useT()
  const isEdit = !!job
  const initialWeights = job && job.scoring_weights ? job.scoring_weights : null
  const [form, setForm] = useState(
    job ? { title: job.title, description: job.description, requirements: job.requirements, scoring_weights: initialWeights }
        : { title: '', description: '', requirements: '', scoring_weights: null }
  )
  const [profile, setProfile] = useState(matchWeightProfile(initialWeights))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function applyProfile(p) {
    setProfile(p)
    if (p === 'custom') {
      setForm(f => ({ ...f, scoring_weights: f.scoring_weights || { ...DEFAULT_CUSTOM_WEIGHTS } }))
    } else {
      setForm(f => ({ ...f, scoring_weights: WEIGHT_PROFILES[p] ? { ...WEIGHT_PROFILES[p] } : null }))
    }
  }

  function setWeight(key, value) {
    const n = Math.max(0, Math.min(100, parseInt(value, 10) || 0))
    setForm(f => ({ ...f, scoring_weights: { ...(f.scoring_weights || DEFAULT_CUSTOM_WEIGHTS), [key]: n } }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      isEdit ? await api.patch(`/jobs/${job.id}`, form) : await api.post('/jobs', form)
      onSaved()
    } catch (err) {
      setError(err.response?.data?.detail || t('jobs.genericError'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-lg p-6">
        <h2 className="text-lg font-semibold text-content mb-5">
          {isEdit ? t('jobs.editTitle') : t('jobs.createTitle')}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-content mb-1.5">{t('jobs.fieldTitle')}</label>
            <input className="input" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} required />
          </div>
          <div>
            <label className="block text-sm font-medium text-content mb-1.5">{t('jobs.fieldDescription')}</label>
            <textarea className="input min-h-[80px] resize-none" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} required />
          </div>
          <div>
            <label className="block text-sm font-medium text-content mb-1.5">{t('jobs.fieldRequirements')}</label>
            <textarea className="input min-h-[80px] resize-none" value={form.requirements} onChange={e => setForm(f => ({ ...f, requirements: e.target.value }))} required />
          </div>
          <div>
            <label className="block text-sm font-medium text-content mb-1.5">{t('jobs.weightsLabel')}</label>
            <div className="flex flex-wrap gap-2 mb-2">
              {['balanced', 'technical', 'management', 'custom'].map(p => (
                <button key={p} type="button" onClick={() => applyProfile(p)}
                  className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${profile === p ? 'bg-brand-600 text-white border-brand-600' : 'border-line text-muted hover:bg-surface-muted'}`}>
                  {t(`jobs.weightProfile.${p}`)}
                </button>
              ))}
            </div>
            <p className="text-xs text-faint mb-2">{t('jobs.weightsHint')}</p>
            {form.scoring_weights && (
              <div className="grid grid-cols-2 gap-3">
                {WEIGHT_KEYS.map(key => (
                  <div key={key} className="flex items-center gap-2">
                    <span className="text-xs text-muted flex-1">{t(`jobs.weightKey.${key}`)}</span>
                    <input type="number" min="0" max="100" value={form.scoring_weights[key] ?? 0}
                      onChange={e => setWeight(key, e.target.value)}
                      disabled={profile !== 'custom'}
                      className="input w-20 text-sm py-1 disabled:opacity-60" />
                  </div>
                ))}
              </div>
            )}
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex gap-3 pt-2">
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? t('jobs.saving') : t('jobs.save')}
            </button>
            <button type="button" className="btn-secondary" onClick={onClose}>{t('jobs.cancel')}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function JobsPage() {
  const { t } = useT()
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [modal, setModal] = useState(null)
  const [copied, setCopied] = useState(null)

  async function load() {
    const { data } = await api.get('/jobs')
    setJobs(data)
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  async function deleteJob(id) {
    if (!confirm(t('jobs.confirmDelete'))) return
    await api.delete(`/jobs/${id}`)
    load()
  }

  async function toggleActive(job) {
    await api.patch(`/jobs/${job.id}`, { is_active: !job.is_active })
    load()
  }

  function copyLink(link) {
    navigator.clipboard.writeText(link)
    setCopied(link)
    setTimeout(() => setCopied(null), 2000)
  }

  if (loading) return <div className="flex items-center justify-center h-full"><Spinner size="lg" /></div>

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-content">{t('nav.jobs')}</h1>
          <p className="text-muted mt-1">{t('jobs.countSuffix', { count: jobs.length })}</p>
        </div>
        <button className="btn-primary" onClick={() => setModal('create')}>
          <Plus className="w-4 h-4" /> {t('jobs.createButton')}
        </button>
      </div>

      {jobs.length === 0 ? (
        <div className="card py-16 text-center">
          <Briefcase className="w-12 h-12 mx-auto text-faint mb-4" />
          <p className="text-muted font-medium">{t('jobs.emptyTitle')}</p>
          <button className="btn-primary mt-4" onClick={() => setModal('create')}>
            <Plus className="w-4 h-4" /> {t('jobs.createFull')}
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map(job => (
            <div key={job.id} className="card p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-content">{job.title}</h3>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      job.is_active ? 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300' : 'bg-surface-muted text-muted'
                    }`}>{job.is_active ? t('jobs.statusActive') : t('jobs.statusClosed')}</span>
                  </div>
                  <p className="text-sm text-muted line-clamp-2">{job.description}</p>
                  <div className="mt-3 flex items-center gap-2">
                    <code className="text-xs bg-surface-muted border border-line px-2 py-1 rounded text-muted truncate max-w-xs">
                      {job.apply_link}
                    </code>
                    <button onClick={() => copyLink(job.apply_link)}
                      className="p-1.5 rounded-lg hover:bg-surface-muted text-faint hover:text-muted transition-colors">
                      {copied === job.apply_link ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button onClick={() => toggleActive(job)}
                    className="p-2 rounded-lg hover:bg-surface-muted text-faint hover:text-muted transition-colors">
                    {job.is_active ? <ToggleRight className="w-5 h-5 text-green-500" /> : <ToggleLeft className="w-5 h-5" />}
                  </button>
                  <button onClick={() => setModal(job)} className="btn-secondary text-xs px-3 py-1.5">{t('jobs.editButton')}</button>
                  <button onClick={() => deleteJob(job.id)}
                    className="p-2 rounded-lg hover:bg-red-50 text-faint hover:text-red-500 transition-colors">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      {modal && (
        <JobModal job={modal === 'create' ? null : modal}
          onClose={() => setModal(null)} onSaved={() => { setModal(null); load() }} />
      )}
    </div>
  )
}
