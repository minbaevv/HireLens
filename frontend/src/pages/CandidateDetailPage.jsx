import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api/client'
import ScoreBadge from '../components/ScoreBadge'
import StatusBadge from '../components/StatusBadge'
import RecommendationBadge from '../components/RecommendationBadge'
import Spinner from '../components/Spinner'
import { useT } from '../i18n'
import { ArrowLeft, CheckCircle, XCircle, FileText, Download, AlertTriangle, ClipboardCheck, RefreshCw } from 'lucide-react'
import SchedulingCard from '../components/SchedulingCard'
import CodingCard from '../components/CodingCard'

export default function CandidateDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t } = useT()
  const [candidate, setCandidate] = useState(null)
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)

  // Финальное решение (ground truth)
  const [decision, setDecision] = useState('')
  const [feedback, setFeedback] = useState('')
  const [notes, setNotes] = useState('')
  const [savingDecision, setSavingDecision] = useState(false)
  const [tab, setTab] = useState('scoring')
  const [rescoring, setRescoring] = useState(false)

  async function load() {
    const { data } = await api.get(`/candidates/${id}`)
    setCandidate(data)
    setDecision(data.actual_hire_decision || '')
    setFeedback(data.ai_feedback || '')
    setNotes(data.hr_notes || '')
    setLoading(false)
  }

  useEffect(() => { load() }, [id])

  async function updateStatus(status) {
    setUpdating(true)
    await api.patch(`/candidates/${id}/status?new_status=${status}`)
    await load()
    setUpdating(false)
  }

  async function saveDecision() {
    if (!decision) return
    setSavingDecision(true)
    try {
      await api.patch(`/candidates/${id}/final-decision`, {
        actual_hire_decision: decision,
        ai_feedback: feedback || null,
        hr_notes: notes || null,
      })
      await load()
    } finally {
      setSavingDecision(false)
    }
  }

  async function rescore() {
    setRescoring(true)
    try {
      await api.post(`/candidates/${id}/rescore`)
      // Скоринг идёт в фоне (~10-30с) - поллим результат.
      for (let i = 0; i < 8; i++) {
        await new Promise((r) => setTimeout(r, 5000))
        const { data } = await api.get(`/candidates/${id}`)
        if (data.score != null && !data.requires_manual_review) break
      }
      await load()
    } finally {
      setRescoring(false)
    }
  }

  async function downloadPdf() {
    const response = await api.get(`/candidates/${id}/report.pdf`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `candidate_${id}_report.pdf`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  }

  if (loading) return <div className="flex items-center justify-center h-full"><Spinner size="lg" /></div>
  if (!candidate) return null

  const scoreColor = candidate.score >= 75 ? 'text-green-600' : candidate.score >= 50 ? 'text-yellow-600' : 'text-red-600'
  const safeParse = (s, fb) => { try { return JSON.parse(s) } catch { return fb } }
  const confidenceLevel = candidate.confidence_level || (candidate.confidence == null ? null : candidate.confidence >= 0.8 ? 'high' : candidate.confidence >= 0.5 ? 'medium' : 'low')
  const confLabel = confidenceLevel === 'high' ? t('candidateDetail.highConfidence') : confidenceLevel === 'medium' ? t('candidateDetail.mediumConfidence') : confidenceLevel === 'low' ? t('candidateDetail.lowConfidence') : ''
  const confBadgeClass = confidenceLevel === 'high' ? 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300' : confidenceLevel === 'medium' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-500/15 dark:text-yellow-300' : 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300'
  const reasoning = candidate.scoring_reasoning ? safeParse(candidate.scoring_reasoning, {}) : {}
  const biasFlags = candidate.bias_flags ? safeParse(candidate.bias_flags, []) : []
  const crossVal = candidate.cross_validation ? safeParse(candidate.cross_validation, {}) : {}
  const discrepancies = Array.isArray(crossVal.discrepancies) ? crossVal.discrepancies : []
  const evasive = Array.isArray(crossVal.evasive_answers) ? crossVal.evasive_answers : []
  const attribution = candidate.answer_attribution ? safeParse(candidate.answer_attribution, {}) : {}
  const attrQuestions = Array.isArray(attribution.questions) ? attribution.questions : []

  return (
    <div className="p-8 max-w-3xl">
      <button onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-sm text-muted hover:text-content mb-6 transition-colors">
        <ArrowLeft className="w-4 h-4" /> {t('common.back')}
      </button>

      {candidate.requires_manual_review && (
        <div className="mb-4 p-4 rounded-xl bg-amber-50 border border-amber-200 dark:bg-amber-500/10 dark:border-amber-500/30">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">{t('candidateDetail.reviewBanner')}</p>
              <p className="text-xs text-amber-700 dark:text-amber-400 mt-0.5">{t('candidateDetail.reviewBannerHint')}</p>
            </div>
          </div>
          <button onClick={rescore} disabled={rescoring}
            className="btn-secondary mt-3 border-amber-300 dark:border-amber-500/40 text-amber-800 dark:text-amber-300">
            <RefreshCw className={`w-4 h-4 ${rescoring ? 'animate-spin' : ''}`} />
            {rescoring ? t('candidateDetail.rescoreRunning') : t('candidateDetail.rescore')}
          </button>
        </div>
      )}

      <div className="card p-6 mb-4">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold text-content">{candidate.name}</h1>
            <p className="text-muted text-sm mt-0.5">{candidate.email}</p>
            <div className="flex items-center gap-3 mt-3">
              <StatusBadge status={candidate.status} />
              <RecommendationBadge value={candidate.recommendation} />
            </div>
          </div>
          {candidate.score != null && (
            <div className="text-center">
              <p className={`text-4xl font-black ${scoreColor}`}>{Math.round(candidate.score)}</p>
              <p className="text-xs text-faint mt-0.5">{t('candidateDetail.outOf100')}</p>
            </div>
          )}
        </div>
        <div className="flex flex-wrap gap-3 mt-5 pt-5 border-t border-line">
          {candidate.status !== 'hired' && candidate.status !== 'rejected' && (
            <>
              <button onClick={() => updateStatus('hired')} disabled={updating}
                className="btn-primary bg-green-600 hover:bg-green-700">
                <CheckCircle className="w-4 h-4" /> {t('candidateDetail.accept')}
              </button>
              <button onClick={() => updateStatus('rejected')} disabled={updating} className="btn-danger">
                <XCircle className="w-4 h-4" /> {t('candidateDetail.reject')}
              </button>
            </>
          )}
          <button onClick={downloadPdf} className="btn-secondary">
            <Download className="w-4 h-4" /> {t('candidateDetail.downloadPdf')}
          </button>
        </div>
      </div>

      {candidate.summary && (
        <div className="card p-6 mb-4">
          <h2 className="font-semibold text-content mb-3">{t('candidateDetail.aiSummaryTitle')}</h2>
          <p className="text-sm text-content leading-relaxed">{candidate.summary}</p>
        </div>
      )}

      {/* Batch#1: Scoring / Bias tabs */}
      {(candidate.technical_score != null || biasFlags.length > 0 || discrepancies.length > 0 || evasive.length > 0) && (
        <div className="card p-6 mb-4">
          <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
            <div className="flex gap-2">
              <button type="button" onClick={() => setTab('scoring')}
                className={`px-3 py-1.5 text-sm font-medium rounded-lg border transition-colors ${tab === 'scoring' ? 'bg-brand-600 text-white border-brand-600' : 'bg-surface text-muted border-line hover:bg-surface-muted'}`}>
                {t('candidateDetail.tabScoring')}
              </button>
              <button type="button" onClick={() => setTab('bias')}
                className={`px-3 py-1.5 text-sm font-medium rounded-lg border transition-colors ${tab === 'bias' ? 'bg-brand-600 text-white border-brand-600' : 'bg-surface text-muted border-line hover:bg-surface-muted'}`}>
                {t('candidateDetail.tabBias')}{biasFlags.length > 0 ? ` (${biasFlags.length})` : ''}
              </button>
            </div>
            {tab === 'scoring' && confidenceLevel && (
              <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${confBadgeClass}`}>
                {confLabel}{candidate.score_range ? ` · ${candidate.score_range}` : ''}
              </span>
            )}
          </div>

          {tab === 'scoring' && (
            <>
              {candidate.technical_score != null && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="border border-line rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-content">{t('candidateDetail.technicalSkills')}</span>
                      <ScoreBadge score={candidate.technical_score} />
                    </div>
                    {reasoning.technical_skills && <p className="text-xs text-muted">{reasoning.technical_skills}</p>}
                  </div>
                  <div className="border border-line rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-content">{t('candidateDetail.softSkills')}</span>
                      <ScoreBadge score={candidate.soft_skills_score} />
                    </div>
                    {reasoning.soft_skills && <p className="text-xs text-muted">{reasoning.soft_skills}</p>}
                  </div>
                  <div className="border border-line rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-content">{t('candidateDetail.experience')}</span>
                      <ScoreBadge score={candidate.experience_score} />
                    </div>
                    {reasoning.experience && <p className="text-xs text-muted">{reasoning.experience}</p>}
                  </div>
                  <div className="border border-line rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-content">{t('candidateDetail.motivation')}</span>
                      <ScoreBadge score={candidate.motivation_score} />
                    </div>
                    {reasoning.motivation && <p className="text-xs text-muted">{reasoning.motivation}</p>}
                  </div>
                </div>
              )}
              {discrepancies.length > 0 && (
                <div className="mt-4 p-3 bg-amber-50 border border-amber-200 dark:bg-amber-500/10 dark:border-amber-500/30 rounded-lg">
                  <p className="text-xs font-semibold text-amber-800 dark:text-amber-300 mb-2">{t('candidateDetail.discrepanciesTitle')}</p>
                  <ul className="text-xs text-amber-700 dark:text-amber-400 space-y-1 list-disc list-inside">
                    {discrepancies.map((d, idx) => <li key={idx}>{typeof d === 'string' ? d : JSON.stringify(d)}</li>)}
                  </ul>
                </div>
              )}
              {evasive.length > 0 && (
                <div className="mt-4 p-3 bg-surface-muted border border-line rounded-lg">
                  <p className="text-xs font-semibold text-content mb-2">{t('candidateDetail.evasiveTitle')}</p>
                  <ul className="text-xs text-muted space-y-1 list-disc list-inside">
                    {evasive.map((ev, idx) => <li key={idx}>{typeof ev === 'string' ? ev : JSON.stringify(ev)}</li>)}
                  </ul>
                </div>
              )}
              {attrQuestions.length > 0 && (
                <div className="mt-4 p-3 bg-surface-muted border border-line rounded-lg">
                  <p className="text-xs font-semibold text-content mb-2">{t('candidateDetail.interviewQuestionsTitle')}</p>
                  <ul className="text-xs text-muted space-y-1">
                    {attrQuestions.map((q) => <li key={q.n}><span className="font-semibold">Q{q.n}</span>: {q.question}</li>)}
                  </ul>
                </div>
              )}
              {candidate.technical_score == null && discrepancies.length === 0 && evasive.length === 0 && (
                <p className="text-sm text-faint">{t('candidateDetail.noScoringData')}</p>
              )}
            </>
          )}

          {tab === 'bias' && (
            biasFlags.length > 0 ? (
              <div className="p-3 bg-yellow-50 border border-yellow-200 dark:bg-yellow-500/10 dark:border-yellow-500/30 rounded-lg">
                <p className="text-xs font-semibold text-yellow-800 dark:text-yellow-300 mb-2">{t('candidateDetail.biasWarning')}</p>
                <ul className="text-xs text-yellow-700 dark:text-yellow-400 space-y-1 list-disc list-inside">
                  {biasFlags.map((flag, idx) => <li key={idx}>{typeof flag === 'string' ? flag : (flag.detail || flag.category || JSON.stringify(flag))}</li>)}
                </ul>
              </div>
            ) : (
              <p className="text-sm text-faint">{t('candidateDetail.biasNone')}</p>
            )
          )}
        </div>
      )}
      {candidate.anti_cheat_score != null && (
        <div className="card p-6 mb-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-content">{t('candidateDetail.antiCheatTitle')}</h2>
            <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${
              candidate.anti_cheat_score >= 60 ? 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300' :
              candidate.anti_cheat_score >= 30 ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-500/15 dark:text-yellow-300' : 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300'
            }`}>
              {Math.round(candidate.anti_cheat_score)}/100
            </span>
          </div>
          {candidate.anti_cheat_flags && candidate.anti_cheat_flags.length > 0 ? (
            <ul className="text-sm text-content space-y-1.5 list-disc list-inside">
              {candidate.anti_cheat_flags.map((flag, i) => <li key={i}>{flag}</li>)}
            </ul>
          ) : (
            <p className="text-sm text-faint">{t('candidateDetail.antiCheatNoFlags')}</p>
          )}
          <p className="text-xs text-faint mt-3">{t('candidateDetail.antiCheatDisclaimer')}</p>
        </div>
      )}

      {/* B4 — Планирование интервью (Google Calendar) */}
      <SchedulingCard candidateId={id} />

      {/* GAP-5 — Технический тест (coding-ассессмент) */}
      <CodingCard candidateId={id} />

      {/* 1.1/1.2 — Финальное решение HR (ground truth для измерения точности AI) */}
      <div className="card p-6 mb-4">
        <div className="flex items-center gap-2 mb-1">
          <ClipboardCheck className="w-4 h-4 text-brand-600" />
          <h2 className="font-semibold text-content">{t('candidateDetail.finalDecisionTitle')}</h2>
        </div>
        <p className="text-xs text-faint mb-4">{t('candidateDetail.finalDecisionHint')}</p>

        {candidate.actual_hire_decision && (
          <div className="mb-4 flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 dark:bg-green-500/10 dark:border-green-500/30 dark:text-green-400 rounded-lg px-3 py-2">
            <CheckCircle className="w-4 h-4" />
            {t('candidateDetail.decisionRecorded')}
          </div>
        )}

        <label className="block text-xs font-medium text-muted mb-1.5">{t('candidateDetail.decisionLabel')}</label>
        <div className="flex flex-wrap gap-2 mb-4">
          {[
            { v: 'hired',          label: t('candidateDetail.decisionHired'),    on: 'bg-green-600 text-white border-green-600' },
            { v: 'rejected_final', label: t('candidateDetail.decisionRejected'), on: 'bg-red-600 text-white border-red-600' },
            { v: 'pending',        label: t('candidateDetail.decisionPending'),  on: 'bg-gray-700 text-white border-gray-700' },
          ].map(opt => (
            <button key={opt.v} type="button" onClick={() => setDecision(opt.v)}
              className={`px-3 py-1.5 text-sm font-medium rounded-lg border transition-colors ${
                decision === opt.v ? opt.on : 'bg-surface text-muted border-line hover:bg-surface-muted'
              }`}>
              {opt.label}
            </button>
          ))}
        </div>

        <label className="block text-xs font-medium text-muted mb-1.5">{t('candidateDetail.aiWasQuestion')}</label>
        <div className="flex flex-wrap gap-2 mb-4">
          {[
            { v: 'correct',   label: t('candidateDetail.aiCorrect'),   on: 'bg-green-600 text-white border-green-600' },
            { v: 'partial',   label: t('candidateDetail.aiPartial'),   on: 'bg-yellow-500 text-white border-yellow-500' },
            { v: 'incorrect', label: t('candidateDetail.aiIncorrect'), on: 'bg-red-600 text-white border-red-600' },
          ].map(opt => (
            <button key={opt.v} type="button" onClick={() => setFeedback(f => f === opt.v ? '' : opt.v)}
              className={`px-3 py-1.5 text-sm font-medium rounded-lg border transition-colors ${
                feedback === opt.v ? opt.on : 'bg-surface text-muted border-line hover:bg-surface-muted'
              }`}>
              {opt.label}
            </button>
          ))}
        </div>

        <label className="block text-xs font-medium text-muted mb-1.5">{t('candidateDetail.hrNotes')}</label>
        <textarea className="input min-h-[72px] mb-4" maxLength={1000}
          placeholder={t('candidateDetail.hrNotesPlaceholder')}
          value={notes} onChange={e => setNotes(e.target.value)} />

        <button onClick={saveDecision} disabled={!decision || savingDecision} className="btn-primary">
          <ClipboardCheck className="w-4 h-4" /> {t('candidateDetail.saveDecision')}
        </button>
      </div>

      {candidate.resume_text && (
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-3">
            <FileText className="w-4 h-4 text-faint" />
            <h2 className="font-semibold text-content">{t('candidateDetail.resumeTitle')}</h2>
          </div>
          <pre className="text-sm text-content whitespace-pre-wrap font-sans leading-relaxed">{candidate.resume_text}</pre>
        </div>
      )}
    </div>
  )
}
