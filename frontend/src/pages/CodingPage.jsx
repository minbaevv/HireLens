import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Code2, Plus, Pencil, Trash2, Eye, EyeOff, ChevronDown, ChevronUp } from 'lucide-react'
import api from '../api/client'
import Spinner from '../components/Spinner'
import { useT } from '../i18n'
import { useAuth } from '../hooks/useAuth'

const EMPTY_FORM = {
  title: '', description: '', language: 'python', difficulty: 'medium',
  starter_code: '', reference_solution: '', required_keywords: '',
  max_score: 100, time_limit_minutes: '',
}

function diffLabel(d, t) {
  if (d === 'easy') return t('coding.diffEasy')
  if (d === 'hard') return t('coding.diffHard')
  return t('coding.diffMedium')
}

function statusLabel(st, t) {
  if (st === 'submitted') return t('coding.stSubmitted')
  if (st === 'reviewed') return t('coding.stReviewed')
  return t('coding.stAssigned')
}

export default function CodingPage() {
  const { t } = useT()
  const { canWrite } = useAuth()
  const [tab, setTab] = useState('challenges')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [challenges, setChallenges] = useState([])
  const [submissions, setSubmissions] = useState([])

  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  function handleErr(err, fallback) {
    if (err.response?.status === 403) setError(t('coding.forbidden'))
    else setError(err.response?.data?.detail || fallback)
  }

  async function load() {
    setLoading(true)
    setError('')
    try {
      const [c, s] = await Promise.all([
        api.get('/coding/challenges', { params: { include_inactive: true } }),
        api.get('/coding/submissions'),
      ])
      setChallenges(c.data)
      setSubmissions(s.data)
    } catch (err) {
      handleErr(err, t('coding.errorLoad'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [])

  const challengeTitle = (id) => challenges.find(c => c.id === id)?.title || ('#' + id)

  function openCreate() {
    setEditing(null)
    setForm(EMPTY_FORM)
    setShowForm(true)
  }

  function openEdit(c) {
    setEditing(c.id)
    setForm({
      title: c.title, description: c.description, language: c.language,
      difficulty: c.difficulty, starter_code: c.starter_code || '',
      reference_solution: c.reference_solution || '',
      required_keywords: (c.required_keywords || []).join(', '),
      max_score: c.max_score, time_limit_minutes: c.time_limit_minutes ?? '',
    })
    setShowForm(true)
  }

  async function saveChallenge(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    const payload = {
      title: form.title.trim(),
      description: form.description.trim(),
      language: form.language.trim() || 'python',
      difficulty: form.difficulty,
      starter_code: form.starter_code.trim() || null,
      reference_solution: form.reference_solution.trim() || null,
      required_keywords: form.required_keywords.trim()
        ? form.required_keywords.split(',').map(s => s.trim()).filter(Boolean)
        : null,
      max_score: Number(form.max_score) || 100,
      time_limit_minutes: form.time_limit_minutes ? Number(form.time_limit_minutes) : null,
    }
    try {
      if (editing) await api.patch(`/coding/challenges/${editing}`, payload)
      else await api.post('/coding/challenges', payload)
      setShowForm(false)
      await load()
    } catch (err) {
      handleErr(err, t('coding.errorSave'))
    } finally {
      setSaving(false)
    }
  }

  async function toggleActive(c) {
    try {
      await api.patch(`/coding/challenges/${c.id}`, { is_active: !c.is_active })
      await load()
    } catch (err) { handleErr(err, t('coding.errorSave')) }
  }

  async function removeChallenge(c) {
    if (!window.confirm(t('coding.deleteConfirm'))) return
    try {
      await api.delete(`/coding/challenges/${c.id}`)
      await load()
    } catch (err) { handleErr(err, t('coding.errorSave')) }
  }

  if (loading) return <div className="p-8"><Spinner /></div>

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center gap-3 mb-1">
        <Code2 className="w-6 h-6 text-brand-600" />
        <h1 className="text-2xl font-bold text-content">{t('coding.title')}</h1>
      </div>
      <p className="text-sm text-muted mb-6">{t('coding.subtitle')}</p>

      {error && <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 text-red-700 dark:bg-red-500/15 dark:text-red-300 text-sm">{error}</div>}

      <div className="flex gap-2 mb-6 border-b border-line">
        {['challenges', 'submissions'].map(k => (
          <button key={k} type="button" onClick={() => setTab(k)}
            className={`px-4 py-2 text-sm font-medium -mb-px border-b-2 transition-colors ${tab === k ? 'border-brand-600 text-brand-700 dark:text-brand-300' : 'border-transparent text-muted hover:text-content'}`}>
            {k === 'challenges' ? t('coding.tabChallenges') : t('coding.tabSubmissions')}
          </button>
        ))}
      </div>

      {tab === 'challenges' && (
        <ChallengesTab
          challenges={challenges} t={t} canWrite={canWrite}
          onCreate={openCreate} onEdit={openEdit}
          onToggle={toggleActive} onDelete={removeChallenge}
        />
      )}

      {tab === 'submissions' && (
        <SubmissionsTab
          submissions={submissions} challengeTitle={challengeTitle}
          t={t} onReviewed={load} canWrite={canWrite}
        />
      )}

      {showForm && (
        <ChallengeForm
          form={form} setForm={setForm} editing={editing}
          saving={saving} onSubmit={saveChallenge}
          onClose={() => setShowForm(false)} t={t}
        />
      )}
    </div>
  )
}

function ChallengesTab({ challenges, t, canWrite, onCreate, onEdit, onToggle, onDelete }) {
  return (
    <div>
      {canWrite && (
      <div className="flex justify-end mb-4">
        <button type="button" onClick={onCreate} className="btn-primary inline-flex items-center gap-1">
          <Plus className="w-4 h-4" />{t('coding.newChallenge')}
        </button>
      </div>
      )}
      {challenges.length === 0 ? (
        <div className="text-center py-12 text-muted">
          <p className="font-medium">{t('coding.noChallenges')}</p>
          <p className="text-sm text-faint mt-1">{t('coding.emptyHint')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {challenges.map(c => (
            <div key={c.id} className="bg-surface border border-line rounded-xl p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-semibold text-content truncate">{c.title}</h3>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-surface-muted text-muted">{c.language}</span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-surface-muted text-muted">{diffLabel(c.difficulty, t)}</span>
                    {!c.is_active && <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">{t('coding.inactiveLabel')}</span>}
                  </div>
                  <p className="text-sm text-muted mt-1 line-clamp-2 whitespace-pre-wrap">{c.description}</p>
                  <p className="text-xs text-faint mt-2">
                    {c.max_score} {t('coding.pts')} · {c.time_limit_minutes ? `${c.time_limit_minutes} ${t('coding.min')}` : t('coding.noLimit')}
                  </p>
                </div>
                {canWrite && (
                <div className="flex items-center gap-1 shrink-0">
                  <button type="button" onClick={() => onToggle(c)} title={c.is_active ? t('coding.deactivate') : t('coding.activate')} className="p-2 rounded-lg text-muted hover:bg-surface-muted">
                    {c.is_active ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                  </button>
                  <button type="button" onClick={() => onEdit(c)} title={t('coding.edit')} className="p-2 rounded-lg text-muted hover:bg-surface-muted">
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button type="button" onClick={() => onDelete(c)} title={t('coding.delete')} className="p-2 rounded-lg text-red-500 hover:bg-red-50 dark:hover:bg-red-500/15">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ChallengeForm({ form, setForm, editing, saving, onSubmit, onClose, t }) {
  const upd = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }))
  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-start justify-center overflow-auto py-10 px-4">
      <form onSubmit={onSubmit} className="bg-surface rounded-2xl border border-line w-full max-w-2xl p-6 space-y-4">
        <h2 className="text-lg font-bold text-content">{editing ? t('coding.editChallenge') : t('coding.createChallenge')}</h2>

        <div>
          <label className="block text-sm font-medium text-content mb-1">{t('coding.fTitle')}</label>
          <input className="input" value={form.title} onChange={upd('title')} required maxLength={255} />
        </div>
        <div>
          <label className="block text-sm font-medium text-content mb-1">{t('coding.fDescription')}</label>
          <textarea className="input min-h-[120px] font-mono text-sm" value={form.description} onChange={upd('description')} required />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-content mb-1">{t('coding.fLanguage')}</label>
            <input className="input" value={form.language} onChange={upd('language')} placeholder="python" />
          </div>
          <div>
            <label className="block text-sm font-medium text-content mb-1">{t('coding.fDifficulty')}</label>
            <select className="input" value={form.difficulty} onChange={upd('difficulty')}>
              <option value="easy">{t('coding.diffEasy')}</option>
              <option value="medium">{t('coding.diffMedium')}</option>
              <option value="hard">{t('coding.diffHard')}</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-content mb-1">{t('coding.fMaxScore')}</label>
            <input type="number" min={1} max={1000} className="input" value={form.max_score} onChange={upd('max_score')} />
          </div>
          <div>
            <label className="block text-sm font-medium text-content mb-1">{t('coding.fTimeLimit')}</label>
            <input type="number" min={1} max={600} className="input" value={form.time_limit_minutes} onChange={upd('time_limit_minutes')} />
            <p className="text-xs text-faint mt-1">{t('coding.timeLimitHint')}</p>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-content mb-1">{t('coding.fKeywords')}</label>
          <input className="input" value={form.required_keywords} onChange={upd('required_keywords')} placeholder="def, return, for" />
          <p className="text-xs text-faint mt-1">{t('coding.keywordsHint')}</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-content mb-1">{t('coding.fStarter')}</label>
          <textarea className="input min-h-[80px] font-mono text-sm" value={form.starter_code} onChange={upd('starter_code')} />
        </div>
        <div>
          <label className="block text-sm font-medium text-content mb-1">{t('coding.fReference')}</label>
          <textarea className="input min-h-[80px] font-mono text-sm" value={form.reference_solution} onChange={upd('reference_solution')} />
          <p className="text-xs text-faint mt-1">{t('coding.referenceHint')}</p>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="btn-secondary">{t('coding.cancel')}</button>
          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? t('coding.saving') : (editing ? t('coding.save') : t('coding.create'))}
          </button>
        </div>
      </form>
    </div>
  )
}

function SubmissionsTab({ submissions, challengeTitle, t, onReviewed, canWrite }) {
  if (submissions.length === 0) {
    return (
      <div className="text-center py-12 text-muted">
        <p className="font-medium">{t('coding.noSubmissions')}</p>
        <p className="text-sm text-faint mt-1">{t('coding.submissionsHint')}</p>
      </div>
    )
  }
  return (
    <div className="space-y-3">
      {submissions.map(s => (
        <SubmissionRow key={s.id} s={s} challengeTitle={challengeTitle} t={t} onReviewed={onReviewed} canWrite={canWrite} />
      ))}
    </div>
  )
}

function SubmissionRow({ s, challengeTitle, t, onReviewed, canWrite }) {
  const [open, setOpen] = useState(false)
  const [manualScore, setManualScore] = useState(s.manual_score ?? '')
  const [notes, setNotes] = useState(s.reviewer_notes ?? '')
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')
  const [okMsg, setOkMsg] = useState('')

  const fb = s.auto_feedback

  async function submitReview(e) {
    e.preventDefault()
    setSaving(true); setErr(''); setOkMsg('')
    try {
      await api.post(`/coding/submissions/${s.id}/review`, {
        manual_score: Number(manualScore) || 0,
        reviewer_notes: notes.trim() || null,
      })
      setOkMsg(t('coding.reviewedOk'))
      onReviewed()
    } catch (e2) {
      setErr(e2.response?.data?.detail || t('coding.errorSave'))
    } finally { setSaving(false) }
  }

  return (
    <div className="bg-surface border border-line rounded-xl">
      <button type="button" onClick={() => setOpen(o => !o)} className="w-full flex items-center justify-between gap-3 p-4 text-left">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-content truncate">{challengeTitle(s.challenge_id)}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${s.status === 'reviewed' ? 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300' : s.status === 'submitted' ? 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300' : 'bg-surface-muted text-muted'}`}>{statusLabel(s.status, t)}</span>
            {s.requires_manual_review && s.status !== 'reviewed' && <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">{t('coding.needsReview')}</span>}
          </div>
          <p className="text-xs text-faint mt-1">
            <Link to={`/candidates/${s.candidate_id}`} className="text-brand-600 hover:underline" onClick={e => e.stopPropagation()}>{t('coding.colCandidate')} #{s.candidate_id}</Link>
            {' · '}{t('coding.colAuto')}: {s.auto_score ?? '—'}
            {s.manual_score != null && ` · ${t('coding.colFinal')}: ${s.manual_score}`}
          </p>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-muted shrink-0" /> : <ChevronDown className="w-4 h-4 text-muted shrink-0" />}
      </button>

      {open && (
        <div className="px-4 pb-4 border-t border-line pt-4 space-y-4">
          {fb?.checks && (
            <div>
              <p className="text-xs font-semibold text-muted mb-2">{t('coding.autoChecks')}</p>
              <ul className="space-y-1">
                {fb.checks.map((ch, i) => (
                  <li key={i} className="text-sm flex items-center gap-2">
                    <span className={ch.passed === true ? 'text-green-600' : ch.passed === false ? 'text-red-500' : 'text-faint'}>
                      {ch.passed === true ? '✓' : ch.passed === false ? '✕' : '—'}
                    </span>
                    <span className="text-content">{ch.name}</span>
                    {ch.detail && <span className="text-faint">({ch.detail})</span>}
                  </li>
                ))}
              </ul>
              <p className="text-xs text-faint mt-2">{t('coding.note')}</p>
            </div>
          )}

          <div>
            <p className="text-xs font-semibold text-muted mb-2">{t('coding.submittedCode')}</p>
            {s.submitted_code
              ? <pre className="bg-surface-muted text-content p-3 rounded-lg text-xs font-mono overflow-auto max-h-72 whitespace-pre-wrap">{s.submitted_code}</pre>
              : <p className="text-sm text-faint">{t('coding.noCode')}</p>}
          </div>

          {canWrite && s.status !== 'assigned' && (
            <form onSubmit={submitReview} className="space-y-3 border-t border-line pt-4">
              <div>
                <label className="block text-sm font-medium text-content mb-1">{t('coding.manualScore')}</label>
                <input type="number" min={0} max={1000} className="input max-w-[160px]" value={manualScore} onChange={e => setManualScore(e.target.value)} required />
              </div>
              <div>
                <label className="block text-sm font-medium text-content mb-1">{t('coding.reviewerNotes')}</label>
                <textarea className="input min-h-[70px]" value={notes} onChange={e => setNotes(e.target.value)} placeholder={t('coding.reviewNotesPh')} />
              </div>
              {err && <p className="text-sm text-red-500">{err}</p>}
              {okMsg && <p className="text-sm text-green-600">{okMsg}</p>}
              <button type="submit" disabled={saving} className="btn-primary">{saving ? t('coding.saving') : t('coding.saveReview')}</button>
            </form>
          )}
        </div>
      )}
    </div>
  )
}
