import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import api from '../api/client'
import { useAuth } from '../hooks/useAuth'
import { useT } from '../i18n'
import AnimatedBackground from '../components/AnimatedBackground'

export default function VerifyEmailPage() {
  const [params] = useSearchParams()
  const email = params.get('email') || ''
  const navigate = useNavigate()
  const { login } = useAuth()
  const { t } = useT()

  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [cooldown, setCooldown] = useState(0)

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = setTimeout(() => setCooldown(cooldown - 1), 1000)
    return () => clearTimeout(timer)
  }, [cooldown])

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const resp = await api.post('/auth/verify-email', { email, code })
      login(resp.data.access_token)
      navigate('/')
    } catch (err) {
      setError(err?.response?.data?.detail || t('verify.errorDefault'))
    } finally {
      setLoading(false)
    }
  }

  const resend = async () => {
    if (cooldown > 0) return
    setError('')
    setNotice('')
    try {
      await api.post('/auth/resend-code', { email })
      setNotice(t('verify.resent'))
      setCooldown(60)
    } catch (err) {
      setError(err?.response?.data?.detail || t('verify.errorDefault'))
      setCooldown(60)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas px-4">
      <AnimatedBackground variant="auth" />
      <div className="relative z-10 card p-8 w-full max-w-md backdrop-blur-xl bg-surface/90">
        <h1 className="text-2xl font-bold text-content mb-1">{t('verify.title')}</h1>
        <p className="text-sm text-muted mb-3">
          {t('verify.subtitle')} <span className="font-medium text-content">{email}</span>
        </p>
        <div className="mb-6 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/30 text-amber-700 dark:text-amber-300 text-sm px-3 py-2 rounded-lg">
          {t('verify.spamHint')}
        </div>

        {error && (
          <div className="mb-4 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 text-red-700 dark:text-red-300 text-sm px-3 py-2 rounded-lg">
            {error}
          </div>
        )}
        {notice && (
          <div className="mb-4 bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/30 text-green-700 dark:text-green-300 text-sm px-3 py-2 rounded-lg">
            {notice}
          </div>
        )}

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-content mb-1">{t('verify.codeLabel')}</label>
            <input
              type="text"
              inputMode="numeric"
              autoFocus
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
              className="input w-full text-center text-2xl tracking-[0.5em] font-mono"
              placeholder="000000"
            />
          </div>
          <button type="submit" disabled={loading || code.length < 6} className="btn-primary w-full">
            {loading ? t('verify.loading') : t('verify.submit')}
          </button>
        </form>

        <div className="mt-4 flex items-center justify-between text-sm">
          <button type="button" onClick={resend} disabled={cooldown > 0} className="text-brand-600 hover:underline disabled:text-muted disabled:no-underline">
            {cooldown > 0 ? t('verify.resendIn', { sec: cooldown }) : t('verify.resend')}
          </button>
          <Link to="/login" className="text-muted hover:underline">{t('verify.backToLogin')}</Link>
        </div>
      </div>
    </div>
  )
}
