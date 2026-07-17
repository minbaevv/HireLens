import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import { Code2, CheckCircle } from 'lucide-react'
import Spinner from '../components/Spinner'
import LanguageSwitcher from '../components/LanguageSwitcher'
import { useT } from '../i18n'

export default function CodingChallengePage() {
  const { token } = useParams()
  const { t } = useT()
  const [challenge, setChallenge] = useState(null)
  const [loading, setLoading] = useState(true)
  const [code, setCode] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    axios.get(`/api/coding/public/${token}`)
      .then(r => {
        setChallenge(r.data)
        if (r.data.status === 'reviewed' || r.data.status === 'submitted') setDone(true)
        if (r.data.starter_code) setCode(r.data.starter_code)
      })
      .catch(() => setChallenge(null))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  async function handleSubmit(e) {
    e.preventDefault()
    setError(''); setSubmitting(true)
    try {
      await axios.post(`/api/coding/public/${token}/submit`, { code })
      setDone(true)
    } catch (err) {
      if (err.response?.status === 409) setError(t('codingPublic.alreadyDone'))
      else setError(err.response?.data?.detail || t('codingPublic.error'))
    } finally { setSubmitting(false) }
  }

  if (loading) return <div className="min-h-screen flex items-center justify-center bg-canvas"><Spinner /></div>

  if (!challenge) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-canvas px-4">
        <div className="text-center">
          <h1 className="text-xl font-bold text-content">{t('codingPublic.notFound')}</h1>
          <p className="text-muted mt-2">{t('codingPublic.notFoundHint')}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-canvas">
      <header className="border-b border-line bg-surface">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Code2 className="w-5 h-5 text-brand-600" />
            <span className="font-bold text-content">HireLens</span>
          </div>
          <LanguageSwitcher />
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8">
        {done ? (
          <div className="card p-8 text-center">
            <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
            <h1 className="text-xl font-bold text-content">{t('codingPublic.submittedTitle')}</h1>
            <p className="text-muted mt-2">{t('codingPublic.submittedMsg')}</p>
          </div>
        ) : (
          <>
            <h1 className="text-2xl font-bold text-content mb-2">{challenge.title}</h1>
            <div className="flex items-center gap-2 flex-wrap text-xs text-muted mb-6">
              <span className="px-2 py-0.5 rounded-full bg-surface-muted">{challenge.language}</span>
              <span className="px-2 py-0.5 rounded-full bg-surface-muted">{t('codingPublic.difficulty')}: {challenge.difficulty}</span>
              <span className="px-2 py-0.5 rounded-full bg-surface-muted">{t('codingPublic.maxScore')}: {challenge.max_score}</span>
              {challenge.time_limit_minutes && <span className="px-2 py-0.5 rounded-full bg-surface-muted">{t('codingPublic.timeLimit')}: {challenge.time_limit_minutes} {t('codingPublic.min')}</span>}
            </div>

            <div className="card p-5 mb-6">
              <p className="text-xs font-semibold text-muted mb-2">{t('codingPublic.taskLabel')}</p>
              <p className="text-content whitespace-pre-wrap">{challenge.description}</p>
            </div>

            <form onSubmit={handleSubmit}>
              <label className="block text-sm font-medium text-content mb-1">{t('codingPublic.yourSolution')}</label>
              <textarea
                className="input font-mono text-sm min-h-[280px]"
                value={code}
                onChange={e => setCode(e.target.value)}
                placeholder={t('codingPublic.codePlaceholder')}
                required
              />
              {error && <p className="text-sm text-red-500 mt-2">{error}</p>}
              <button type="submit" disabled={submitting || !code.trim()} className="btn-primary mt-4">
                {submitting ? t('codingPublic.submitting') : t('codingPublic.submit')}
              </button>
            </form>
          </>
        )}
      </main>
    </div>
  )
}
