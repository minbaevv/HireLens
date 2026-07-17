import { useEffect, useState } from 'react'
import api from '../api/client'
import Spinner from '../components/Spinner'
import { useT } from '../i18n'
import { TrendingUp, Users, Briefcase, CheckCircle } from 'lucide-react'

function StatCard({ label, value, icon: Icon, color }) {
  return (
    <div className="card p-5">
      <div className={`inline-flex p-2.5 rounded-xl ${color} mb-3`}>
        <Icon className="w-5 h-5" />
      </div>
      <p className="text-2xl font-bold text-content">{value}</p>
      <p className="text-sm text-muted mt-0.5">{label}</p>
    </div>
  )
}

const STATUS_COLORS = {
  applied:      'bg-blue-500',
  interviewing: 'bg-amber-500',
  completed:    'bg-slate-400',
  hired:        'bg-green-500',
  rejected:     'bg-red-500',
}

export default function AnalyticsPage() {
  const { t } = useT()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.get('/analytics/summary')
      .then(r => setData(r.data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex items-center justify-center h-full"><Spinner size="lg" /></div>
  if (error) return <div className="p-8 text-red-500">{t('analytics.errorPrefix', { message: error })}</div>
  if (!data) return null

  const statusLabels = {
    applied:      t('status.applied'),
    interviewing: t('status.interviewing'),
    completed:    t('status.completed'),
    hired:        t('status.hired'),
    rejected:     t('status.rejected'),
  }

  // by_status — это массив [{status, count}, ...]
  const byStatus = data.by_status || []
  const totalByStatus = byStatus.reduce((sum, s) => sum + s.count, 0)

  const hireRate = data.hire_rate != null ? `${data.hire_rate}%` : '—'
  const avgScore = data.avg_score != null ? Math.round(data.avg_score) : '—'

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-content">{t('nav.analytics')}</h1>
        <p className="text-muted mt-1">{t('analytics.subtitle')}</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label={t('dashboard.statVacancies')}  value={data.total_jobs ?? '—'}       icon={Briefcase}   color="bg-blue-50 text-blue-600 dark:bg-blue-500/15 dark:text-blue-300" />
        <StatCard label={t('dashboard.statCandidates')} value={data.total_candidates ?? '—'} icon={Users}       color="bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300" />
        <StatCard label={t('dashboard.statAvgScore')}   value={avgScore}                     icon={TrendingUp}  color="bg-orange-50 text-orange-600 dark:bg-orange-500/15 dark:text-orange-300" />
        <StatCard label={t('analytics.hireRateLabel')}  value={hireRate}                     icon={CheckCircle} color="bg-green-50 text-green-600 dark:bg-green-500/15 dark:text-green-300" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* По статусам */}
        {byStatus.length > 0 && (
          <div className="card p-6">
            <h2 className="font-semibold text-content mb-4">{t('analytics.byStatusTitle')}</h2>
            <div className="space-y-3">
              {byStatus.map(({ status, count }) => {
                const pct = totalByStatus > 0 ? Math.round((count / totalByStatus) * 100) : 0
                const label = statusLabels[status] || status
                const color = STATUS_COLORS[status] || 'bg-gray-500'
                return (
                  <div key={status}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted">{label}</span>
                      <span className="font-medium text-content">{count} ({pct}%)</span>
                    </div>
                    <div className="h-2 bg-surface-muted rounded-full overflow-hidden">
                      <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Топ вакансии */}
        {data.top_jobs && data.top_jobs.length > 0 && (
          <div className="card p-6">
            <h2 className="font-semibold text-content mb-4">{t('analytics.topJobsTitle')}</h2>
            <div className="space-y-3">
              {data.top_jobs.map((job) => (
                <div key={job.job_id} className="flex items-center justify-between py-2 border-b border-line last:border-0">
                  <div>
                    <p className="text-sm font-medium text-content">{job.title}</p>
                    {job.avg_score != null && (
                      <p className="text-xs text-faint">{t('analytics.avgScoreLine', { score: Math.round(job.avg_score) })}</p>
                    )}
                  </div>
                  <span className="text-sm font-bold text-brand-600">{t('analytics.peopleCount', { count: job.total_candidates })}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
