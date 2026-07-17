import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api/client'
import StatusBadge from '../components/StatusBadge'
import ScoreBadge from '../components/ScoreBadge'
import Spinner from '../components/Spinner'
import { fmtDate } from '../utils/datetime'
import { useT } from '../i18n'
import { useAuth } from '../hooks/useAuth'
import { ArrowLeft, Copy, ExternalLink, Users, UserCheck, UserX, Clock, QrCode, MessageCircle } from 'lucide-react'

export default function JobDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t } = useT()
  const { company } = useAuth()
  const [job, setJob] = useState(null)
  const [candidates, setCandidates] = useState([])
  const [loading, setLoading] = useState(true)
  const [showQR, setShowQR] = useState(false)

  useEffect(() => {
    loadJobAndCandidates()
  }, [id])

  async function loadJobAndCandidates() {
    try {
      const [jobRes, candidatesRes] = await Promise.all([
        api.get(`/jobs/${id}`),
        api.get(`/candidates`, { params: { job_id: id, page: 1, page_size: 100 } })
      ])
      setJob(jobRes.data)
      setCandidates(candidatesRes.data.items || [])
    } catch (err) {
      console.error('Failed to load job details:', err)
    } finally {
      setLoading(false)
    }
  }

  function copyApplyLink() {
    const applyUrl = `${window.location.origin}/apply/${job.apply_token}`
    navigator.clipboard.writeText(applyUrl)
    // TODO: показать toast "Скопировано"
  }

  function generateQRCodeUrl() {
    const applyUrl = `${window.location.origin}/apply/${job.apply_token}`
    // Используем бесплатный QR API
    return `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(applyUrl)}`
  }

  if (loading) return <div className="flex items-center justify-center h-full"><Spinner size="lg" /></div>
  if (!job) return <div className="p-8 text-center text-muted">Вакансия не найдена</div>

  const stats = {
    total: candidates.length,
    applied: candidates.filter(c => c.status === 'applied').length,
    interviewing: candidates.filter(c => c.status === 'interviewing').length,
    completed: candidates.filter(c => c.status === 'completed').length,
    hired: candidates.filter(c => c.status === 'hired').length,
    rejected: candidates.filter(c => c.status === 'rejected').length,
  }

  const applyUrl = `${window.location.origin}/apply/${job.apply_token}`
  const tgBot = company?.telegram_candidate_bot_username
  const tgUrl = tgBot ? `https://t.me/${tgBot}?start=${job.apply_token}` : null

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Назад */}
      <button onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-sm text-muted hover:text-content mb-6 transition-colors">
        <ArrowLeft className="w-4 h-4" /> {t('common.back')}
      </button>

      {/* Заголовок вакансии */}
      <div className="card p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-content">{job.title}</h1>
            <p className="text-sm text-muted mt-1">
              {t('jobs.createdAt')}: {fmtDate(job.created_at)}
            </p>
          </div>
          <span className={`px-3 py-1 rounded-full text-xs font-medium ${
            job.is_active ? 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300' : 'bg-surface-muted text-muted'
          }`}>
            {job.is_active ? t('jobs.active') : t('jobs.inactive')}
          </span>
        </div>

        <div className="mb-4">
          <h3 className="text-sm font-semibold text-content mb-2">{t('jobs.description')}</h3>
          <p className="text-sm text-muted whitespace-pre-wrap">{job.description}</p>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-content mb-2">{t('jobs.requirements')}</h3>
          <p className="text-sm text-muted whitespace-pre-wrap">{job.requirements}</p>
        </div>
      </div>

      {/* Статистика */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
        <div className="card p-4 text-center">
          <Users className="w-5 h-5 text-faint mx-auto mb-2" />
          <p className="text-2xl font-bold text-content">{stats.total}</p>
          <p className="text-xs text-muted">{t('jobDetail.totalCandidates')}</p>
        </div>
        <div className="card p-4 text-center">
          <Clock className="w-5 h-5 text-blue-400 mx-auto mb-2" />
          <p className="text-2xl font-bold text-blue-600">{stats.applied}</p>
          <p className="text-xs text-muted">{t('status.applied')}</p>
        </div>
        <div className="card p-4 text-center">
          <Clock className="w-5 h-5 text-amber-400 mx-auto mb-2" />
          <p className="text-2xl font-bold text-amber-600">{stats.interviewing}</p>
          <p className="text-xs text-muted">{t('status.interviewing')}</p>
        </div>
        <div className="card p-4 text-center">
          <Clock className="w-5 h-5 text-slate-400 mx-auto mb-2" />
          <p className="text-2xl font-bold text-slate-500 dark:text-slate-400">{stats.completed}</p>
          <p className="text-xs text-muted">{t('status.completed')}</p>
        </div>
        <div className="card p-4 text-center">
          <UserCheck className="w-5 h-5 text-green-400 mx-auto mb-2" />
          <p className="text-2xl font-bold text-green-600">{stats.hired}</p>
          <p className="text-xs text-muted">{t('status.hired')}</p>
        </div>
        <div className="card p-4 text-center">
          <UserX className="w-5 h-5 text-red-400 mx-auto mb-2" />
          <p className="text-2xl font-bold text-red-600">{stats.rejected}</p>
          <p className="text-xs text-muted">{t('status.rejected')}</p>
        </div>
      </div>

      {/* Apply Link */}
      <div className="card p-6 mb-6">
        <h2 className="text-lg font-semibold text-content mb-4">{t('jobDetail.applyLinkTitle')}</h2>
        <div className="flex items-center gap-3 mb-4">
          <input
            type="text"
            value={applyUrl}
            readOnly
            className="flex-1 px-4 py-2 border border-line rounded-lg text-sm text-muted bg-surface-muted"
          />
          <button onClick={copyApplyLink} className="btn-secondary">
            <Copy className="w-4 h-4" /> {t('jobDetail.copy')}
          </button>
          <a href={applyUrl} target="_blank" rel="noopener noreferrer" className="btn-secondary">
            <ExternalLink className="w-4 h-4" /> {t('jobDetail.open')}
          </a>
          <button onClick={() => setShowQR(!showQR)} className="btn-secondary">
            <QrCode className="w-4 h-4" />
          </button>
        </div>
        {tgUrl && (
          <div className="mb-4">
            <p className="text-xs text-muted mb-2">{t('jobDetail.telegramLinkLabel')}</p>
            <div className="flex items-center gap-3">
              <input
                type="text"
                value={tgUrl}
                readOnly
                className="flex-1 px-4 py-2 border border-line rounded-lg text-sm text-muted bg-surface-muted"
              />
              <button onClick={() => navigator.clipboard.writeText(tgUrl)} className="btn-secondary">
                <Copy className="w-4 h-4" /> {t('jobDetail.copy')}
              </button>
              <a href={tgUrl} target="_blank" rel="noopener noreferrer" className="btn-secondary">
                <MessageCircle className="w-4 h-4" /> {t('jobDetail.telegramOpen')}
              </a>
            </div>
          </div>
        )}
        {showQR && (
          // QR всегда на белом фоне — иначе тёмная тема ломает сканирование камерой.
          <div className="flex justify-center p-4 bg-white border border-line rounded-lg">
            <img src={generateQRCodeUrl()} alt="QR Code" className="w-64 h-64" />
          </div>
        )}
      </div>

      {/* Список кандидатов */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-content mb-4">
          {t('jobDetail.candidatesTitle')} ({candidates.length})
        </h2>
        {candidates.length === 0 ? (
          <p className="text-sm text-faint text-center py-8">{t('jobDetail.noCandidates')}</p>
        ) : (
          <div className="space-y-3">
            {candidates.map(c => (
              <button
                key={c.id}
                onClick={() => navigate(`/candidates/${c.id}`)}
                className="w-full flex items-center justify-between p-4 bg-surface-muted hover:bg-surface-muted/70 rounded-lg transition-colors text-left"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-content truncate">{c.name}</p>
                  <p className="text-xs text-muted truncate">{c.email}</p>
                </div>
                <div className="flex items-center gap-3 ml-4">
                  {c.score != null && <ScoreBadge score={c.score} />}
                  <StatusBadge status={c.status} />
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
