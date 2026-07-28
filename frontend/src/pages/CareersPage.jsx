import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import { Bot, Briefcase, ArrowRight } from 'lucide-react'
import Spinner from '../components/Spinner'
import LanguageSwitcher from '../components/LanguageSwitcher'
import { useT } from '../i18n'

export default function CareersPage() {
  const { companyId } = useParams()
  const { t } = useT()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    axios.get(`/api/careers/${companyId}`)
      .then(r => setData(r.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [companyId])

  if (loading) return <div className="flex items-center justify-center min-h-screen"><Spinner size="lg" /></div>

  if (error || !data) return (
    <div className="min-h-screen bg-canvas flex items-center justify-center">
      <div className="text-center">
        <p className="text-2xl font-bold text-content mb-2">{t('careers.notFound')}</p>
      </div>
    </div>
  )

  const jobs = data.jobs || []

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 to-brand-100 dark:from-slate-900 dark:to-slate-950 py-10 px-4">
      <div className="w-full max-w-2xl mx-auto">
        <div className="flex justify-end mb-3">
          <LanguageSwitcher />
        </div>
        <div className="text-center mb-8">
          {data.company_logo_url ? (
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4 shadow-lg bg-white overflow-hidden">
              <img src={data.company_logo_url} alt={data.company_name || ''} className="w-full h-full object-contain" />
            </div>
          ) : (
            <div className="inline-flex items-center justify-center w-14 h-14 bg-brand-600 rounded-2xl mb-4 shadow-lg">
              <Bot className="w-7 h-7 text-white" />
            </div>
          )}
          <h1 className="page-title">{data.company_name}</h1>
          <p className="page-subtitle">{t('careers.openPositions')}</p>
        </div>

        {jobs.length === 0 ? (
          <div className="card p-8 text-center">
            <Briefcase className="w-8 h-8 text-faint mx-auto mb-3" />
            <p className="text-muted">{t('careers.empty')}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {jobs.map(job => (
              <a
                key={job.apply_token}
                href={`/apply/${job.apply_token}`}
                className="card p-5 flex items-start justify-between gap-4 hover:border-brand-400 transition-colors group"
              >
                <div className="min-w-0">
                  <h2 className="text-base font-semibold text-content">{job.title}</h2>
                  <p className="text-sm text-muted mt-1">{job.description}</p>
                </div>
                <span className="btn-primary shrink-0 whitespace-nowrap">
                  {t('careers.apply')}
                  <ArrowRight className="w-4 h-4 inline ml-1 group-hover:translate-x-0.5 transition-transform" />
                </span>
              </a>
            ))}
          </div>
        )}

        <p className="text-center text-xs text-faint mt-8">{t('careers.poweredBy')}</p>
      </div>
    </div>
  )
}
