import { useEffect, useState } from 'react'
import api from '../api/client'
import Spinner from '../components/Spinner'
import { useT } from '../i18n'
import { ShieldCheck, AlertTriangle, Flag, Eye } from 'lucide-react'

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

export default function BiasReportPage() {
  const { t } = useT()
  const [data, setData] = useState(null)
  const [jobs, setJobs] = useState([])
  const [jobId, setJobId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.get('/jobs').then(r => setJobs(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.get('/analytics/bias-report', { params: jobId ? { job_id: jobId } : {} })
      .then(r => setData(r.data))
      .catch(e => setError(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false))
  }, [jobId])

  return (
    <div className="p-8">
      <div className="mb-8 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-content">{t('bias.title')}</h1>
          <p className="text-muted mt-1">{t('bias.subtitle')}</p>
        </div>
        <select className="input max-w-xs" value={jobId} onChange={e => setJobId(e.target.value)}>
          <option value="">{t('bias.allJobs')}</option>
          {jobs.map(j => <option key={j.id} value={j.id}>{j.title}</option>)}
        </select>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20"><Spinner size="lg" /></div>
      ) : error ? (
        <div className="p-8 text-red-500">{error}</div>
      ) : data && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard label={t('bias.totalScored')} value={data.total_candidates_scored} icon={ShieldCheck} color="bg-blue-50 text-blue-600 dark:bg-blue-500/15 dark:text-blue-300" />
            <StatCard label={t('bias.flagged')} value={data.flagged_count} icon={Flag} color="bg-red-50 text-red-600 dark:bg-red-500/15 dark:text-red-300" />
            <StatCard label={t('bias.flaggedRate')} value={`${data.flagged_rate}%`} icon={AlertTriangle} color="bg-amber-50 text-amber-600 dark:bg-amber-500/15 dark:text-amber-300" />
            <StatCard label={t('bias.manualReview')} value={data.manual_review_count} icon={Eye} color="bg-orange-50 text-orange-600 dark:bg-orange-500/15 dark:text-orange-300" />
          </div>

          <div className="card p-6">
            <h2 className="font-semibold text-content mb-4">{t('bias.flaggedListTitle')}</h2>
            {(!data.items || data.items.length === 0) ? (
              <p className="text-sm text-faint text-center py-8">{t('bias.noFlags')}</p>
            ) : (
              <div className="space-y-3">
                {data.items.map(item => (
                  <div key={item.candidate_id} className="p-4 bg-surface-muted rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-sm font-semibold text-content">{item.name}</p>
                      <span className="text-xs text-muted">{item.job_title}</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {item.flags.map((f, i) => (
                        <span key={i} className="text-xs px-2 py-1 rounded-full bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300">{f}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
