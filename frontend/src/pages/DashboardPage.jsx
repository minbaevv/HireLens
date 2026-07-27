import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import { Briefcase, Users, TrendingUp, CheckCircle, UserCheck, UserX, BarChart2, Target, AlertTriangle, Gauge } from 'lucide-react'
import Spinner from '../components/Spinner'
import Onboarding from '../components/Onboarding'
import OnboardingChecklist from '../components/OnboardingChecklist'
import { Skeleton, SkeletonStats } from '../components/Skeleton'
import { useT } from '../i18n'
import { useTheme } from '../theme'
import { useCountUp } from '../motion'
import {
  Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts'

const STATUS_COLORS = {
  applied:     '#3b82f6',
  interviewing:'#f59e0b',
  completed:   '#94a3b8',
  hired:       '#10b981',
  rejected:    '#ef4444',
}

const STATUS_LABEL_KEYS = {
  applied:     'dashboard.statusNew',
  interviewing:'dashboard.statusInterviewing',
  completed:   'dashboard.statusCompleted',
  hired:       'dashboard.statusHired',
  rejected:    'dashboard.statusRejected',
}

// Число с count-up при монтировании; нечисловые («—») как есть.
function StatValue({ value }) {
  const isNumeric = typeof value === 'number' && Number.isFinite(value)
  const animated = useCountUp(isNumeric ? value : 0)
  return <p className="text-2xl font-bold text-content font-display">{isNumeric ? animated : value}</p>
}

export default function DashboardPage() {
  const { t } = useT()
  const { isDark } = useTheme()
  const [data, setData]       = useState(null)
  const [candidates, setCandidates] = useState([])
  const [accuracy, setAccuracy] = useState(null)
  const [reviewCount, setReviewCount] = useState(0)
  const [billing, setBilling] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [showOnboarding, setShowOnboarding] = useState(false)

  useEffect(() => {
    Promise.all([
      api.get('/analytics/summary'),
      api.get('/candidates', { params: { page: 1, page_size: 5, sort_by: 'created_at', order: 'desc' } }),
      api.get('/analytics/ai-accuracy').catch(() => ({ data: null })),
      api.get('/candidates', { params: { page: 1, page_size: 1, requires_review: true } }).catch(() => ({ data: { total: 0 } })),
      api.get('/billing/me').catch(() => ({ data: null })),
    ])
      .then(([analytics, cands, acc, review, bill]) => {
        setData(analytics.data)
        setCandidates(cands.data.items)
        setAccuracy(acc.data)
        setReviewCount(review.data?.total ?? 0)
        setBilling(bill.data)
        // Показываем онбординг если нет вакансий и не был показан раньше
        if (analytics.data.total_jobs === 0 && !localStorage.getItem('onboarding_done')) {
          setShowOnboarding(true)
        }
      })
      .catch(() => setError(t('dashboard.loadError')))
      .finally(() => setLoading(false))
  }, [])

  function dismissOnboarding() {
    localStorage.setItem('onboarding_done', '1')
    setShowOnboarding(false)
  }

  if (loading) return (
    <div className="p-8">
      <div className="mb-8 space-y-2">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-4 w-64" />
      </div>
      <SkeletonStats count={4} />
    </div>
  )
  if (error)   return <div className="flex items-center justify-center h-full text-red-500">{error}</div>

  const stats = [
    { label: t('dashboard.statVacancies'), value: data.total_jobs,       sub: t('dashboard.activeJobs', { count: data.active_jobs }),        icon: Briefcase,  color: 'bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300' },
    { label: t('dashboard.statCandidates'), value: data.total_candidates, sub: t('dashboard.interviewsCount', { count: data.total_interviews }), icon: Users,      color: 'bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300' },
    { label: t('dashboard.statHired'),      value: data.hired_count,      sub: t('dashboard.hireRate', { rate: data.hire_rate }),               icon: UserCheck,  color: 'bg-green-50 text-green-600 dark:bg-green-500/15 dark:text-green-300' },
    { label: t('dashboard.statAvgScore'),   value: data.avg_score ?? '—', sub: t('dashboard.completedCount', { count: data.completed_interviews }), icon: TrendingUp, color: 'bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300' },
  ]

  // Квота кандидатов текущего месяца (данные из /billing/me).
  // Баннер появляется с 80% — жёлтый, при исчерпании лимита — красный.
  // candidates_limit === null означает безлимит — баннер не показываем.
  const quotaLimit = billing?.candidates_limit ?? null
  const quotaUsed = billing?.candidates_used ?? 0
  const quotaPct = quotaLimit ? Math.min(100, Math.round((quotaUsed / quotaLimit) * 100)) : 0
  const quotaExceeded = quotaLimit != null && quotaUsed >= quotaLimit
  const showQuota = quotaLimit != null && quotaLimit > 0 && quotaPct >= 80

  const pieData = data.by_status.map(s => ({
    name: t(STATUS_LABEL_KEYS[s.status]) ?? s.status,
    value: s.count,
    color: STATUS_COLORS[s.status] ?? '#94a3b8',
  }))
  const statusTotal = pieData.reduce((sum, s) => sum + s.value, 0)

  const barData = data.top_jobs.map(j => ({
    name: j.title.length > 16 ? j.title.slice(0, 16) + '…' : j.title,
    fullName: j.title,
    candidates: j.total_candidates,
    hired: j.hired_count,
  }))

  // Цвета графиков зависят от темы (сетка/оси/тултип). Серии статусов —
  // насыщенные, читаются в обеих темах, поэтому не меняются.
  const chartGrid = isDark ? '#1e293b' : '#f1f5f9'
  const chartTick = isDark ? '#94a3b8' : '#6b7280'
  const tooltipStyle = {
    backgroundColor: isDark ? '#0f172a' : '#ffffff',
    border: `1px solid ${isDark ? '#334155' : '#e5e7eb'}`,
    borderRadius: '0.5rem',
    color: isDark ? '#f1f5f9' : '#111827',
  }

  // Тултип бар-чарта: показывает полное (не усечённое) название вакансии.
  function BarTooltip({ active, payload }) {
    if (!active || !payload?.length) return null
    const row = payload[0].payload
    return (
      <div style={tooltipStyle} className="px-3 py-2 text-xs">
        <p className="font-semibold mb-1">{row.fullName}</p>
        {payload.map(p => (
          <p key={p.dataKey} style={{ color: p.color }}>{p.name}: {p.value}</p>
        ))}
      </div>
    )
  }

  return (
    <div className="p-8">
      {showOnboarding && <Onboarding onDismiss={dismissOnboarding} />}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-content font-display">{t('nav.dashboard')}</h1>
        <p className="text-muted mt-1">{t('dashboard.subtitle')}</p>
      </div>

      {/* Карточки статистики */}
      <OnboardingChecklist stats={data} />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map(({ label, value, sub, icon: Icon, color }, i) => (
          <div key={label} className="card p-5 animate-fade-up" style={{ animationDelay: `${i * 80}ms` }}>
            <div className={`inline-flex p-2.5 rounded-xl ${color} mb-3`}>
              <Icon className="w-5 h-5" />
            </div>
            <StatValue value={value} />
            <p className="text-sm text-muted mt-0.5">{label}</p>
            <p className="text-xs text-faint mt-1">{sub}</p>
          </div>
        ))}
      </div>

      {/* Лимит кандидатов по тарифу: предупреждение с 80%, красное при исчерпании */}
      {showQuota && (
        <div className={`card p-5 mb-8 flex items-start gap-4 ${
          quotaExceeded
            ? 'bg-red-50 border-red-200 dark:bg-red-500/10 dark:border-red-500/30'
            : 'bg-amber-50 border-amber-200 dark:bg-amber-500/10 dark:border-amber-500/30'
        }`}>
          <div className={`inline-flex p-2.5 rounded-xl shrink-0 ${
            quotaExceeded
              ? 'bg-red-100 text-red-600 dark:bg-red-500/20 dark:text-red-300'
              : 'bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-300'
          }`}>
            <Gauge className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <p className={`text-sm font-semibold ${
                quotaExceeded ? 'text-red-800 dark:text-red-300' : 'text-amber-800 dark:text-amber-300'
              }`}>
                {quotaExceeded ? t('dashboard.quotaExceeded') : t('dashboard.quotaWarning')}
              </p>
              <Link to="/billing" className={`text-sm font-medium whitespace-nowrap hover:underline ${
                quotaExceeded ? 'text-red-700 dark:text-red-400' : 'text-amber-700 dark:text-amber-400'
              }`}>
                {t('dashboard.quotaCta')}
              </Link>
            </div>
            <p className="text-xs text-muted mt-1">
              {t('dashboard.quotaUsed', { used: quotaUsed, limit: quotaLimit })}
              {!quotaExceeded && ` · ${t('dashboard.quotaLeft', { left: quotaLimit - quotaUsed })}`}
            </p>
            <div className="h-2 bg-surface-muted rounded-full overflow-hidden mt-2">
              <div className={`h-full rounded-full transition-all ${quotaExceeded ? 'bg-red-500' : 'bg-amber-500'}`}
                style={{ width: `${quotaPct}%` }} />
            </div>
            <p className="text-xs text-faint mt-1">{t('dashboard.quotaReset')}</p>
          </div>
        </div>
      )}

      {/* AI accuracy + очередь ручной проверки */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="card p-5 flex items-center gap-4">
          <div className="inline-flex p-2.5 rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
            <Target className="w-5 h-5" />
          </div>
          <div>
            <p className="text-2xl font-bold text-content">
              {accuracy && accuracy.total_with_feedback >= 5 ? `${accuracy.accuracy_rate}%` : '—'}
            </p>
            <p className="text-sm text-muted">{t('dashboard.statAiAccuracy')}</p>
            <p className="text-xs text-faint mt-0.5">
              {!accuracy || accuracy.total_with_feedback === 0
                ? t('dashboard.aiAccuracyNoData')
                : accuracy.total_with_feedback < 5
                  ? t('dashboard.aiAccuracyInsufficient', { count: accuracy.total_with_feedback })
                  : t('dashboard.aiAccuracySub', { count: accuracy.total_with_feedback })}
            </p>
          </div>
        </div>

        <Link to="/candidates?review=1"
          className={`sm:col-span-2 card p-5 flex items-center justify-between transition-colors ${
            reviewCount > 0 ? 'bg-amber-50 border-amber-200 hover:bg-amber-100/60 dark:bg-amber-500/10 dark:border-amber-500/30 dark:hover:bg-amber-500/20' : 'hover:bg-surface-muted'
          }`}>
          <div className="flex items-center gap-4">
            <div className={`inline-flex p-2.5 rounded-xl ${reviewCount > 0 ? 'bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-300' : 'bg-surface-muted text-faint'}`}>
              <AlertTriangle className="w-5 h-5" />
            </div>
            <p className={`text-sm font-medium ${reviewCount > 0 ? 'text-amber-800 dark:text-amber-300' : 'text-muted'}`}>
              {t('dashboard.reviewNeeded', { count: reviewCount })}
            </p>
          </div>
          {reviewCount > 0 && (
            <span className="text-sm font-medium text-amber-700 dark:text-amber-400">{t('dashboard.reviewNeededCta')}</span>
          )}
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Распределение по статусам — горизонтальные бары (унифицировано с Аналитикой) */}
        {pieData.length > 0 && (
          <div className="card p-6">
            <h2 className="font-semibold text-content mb-4 flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-faint" /> {t('dashboard.statusChartTitle')}
            </h2>
            <div className="space-y-3">
              {pieData.map(s => {
                const pct = statusTotal > 0 ? Math.round((s.value / statusTotal) * 100) : 0
                return (
                  <div key={s.name}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted">{s.name}</span>
                      <span className="font-medium text-content">{s.value} ({pct}%)</span>
                    </div>
                    <div className="h-2 bg-surface-muted rounded-full overflow-hidden">
                      <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: s.color }} />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Bar — топ вакансии */}
        {barData.length > 0 && (
          <div className="card p-6">
            <h2 className="font-semibold text-content mb-4 flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-faint" /> {t('dashboard.topJobsChartTitle')}
            </h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={barData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartGrid} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: chartTick }} />
                <YAxis tick={{ fontSize: 11, fill: chartTick }} allowDecimals={false} />
                <Tooltip content={<BarTooltip />} cursor={{ fill: isDark ? '#1e293b' : '#f1f5f9' }} />
                <Bar dataKey="candidates" name={t('dashboard.seriesCandidates')} fill="#3b82f6" radius={[4,4,0,0]} />
                <Bar dataKey="hired" name={t('dashboard.seriesHired')} fill="#10b981" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Последние кандидаты */}
      <div className="card">
        <div className="px-6 py-4 border-b border-line flex items-center justify-between">
          <h2 className="font-semibold text-content">{t('dashboard.recentCandidates')}</h2>
          <Link to="/candidates" className="text-sm text-brand-600 hover:underline">{t('dashboard.viewAll')}</Link>
        </div>
        {candidates.length === 0 ? (
          <div className="px-6 py-12 text-center text-faint">
            <Users className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p>{t('dashboard.noCandidatesYet')}</p>
          </div>
        ) : (
          <div className="divide-y divide-line">
            {candidates.slice(0, 5).map(c => (
              <Link key={c.id} to={`/candidates/${c.id}`}
                className="flex items-center justify-between px-6 py-4 hover:bg-surface-muted transition-colors">
                <div>
                  <p className="text-sm font-medium text-content">{c.name}</p>
                  <p className="text-xs text-faint">{c.email}</p>
                </div>
                {c.score != null && (
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                    c.score >= 75 ? 'bg-green-100 text-green-800 dark:bg-green-500/15 dark:text-green-300' :
                    c.score >= 50 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-500/15 dark:text-yellow-300' : 'bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-300'
                  }`}>{Math.round(c.score)}</span>
                )}
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
