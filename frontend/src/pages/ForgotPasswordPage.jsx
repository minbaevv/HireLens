import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api/client'
import { useT } from '../i18n'
import Logo from '../components/Logo'
import LanguageSwitcher from '../components/LanguageSwitcher'
import AnimatedBackground from '../components/AnimatedBackground'

export default function ForgotPasswordPage() {
  const navigate = useNavigate()
  const { t } = useT()
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      // Ответ нейтрален (SEC-11): код придёт, только если email существует и подтверждён.
      await api.post('/auth/forgot-password', { email })
      navigate(`/reset-password?email=${encodeURIComponent(email)}`)
    } catch (err) {
      setError(err.response?.data?.detail || t('forgot.errorDefault'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center p-4">
      <AnimatedBackground variant="auth" />
      <div className="relative z-10 w-full max-w-md">
        <div className="flex justify-end mb-2">
          <LanguageSwitcher />
        </div>
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-brand-400 to-brand-600 rounded-2xl mb-4 shadow-lg shadow-glow-accent">
            <Logo className="w-10 h-10" title="HireLens" gradId="hl-forgot" />
          </div>
          <h1 className="page-title">{t('forgot.title')}</h1>
          <p className="page-subtitle">{t('forgot.subtitle')}</p>
        </div>
        <div className="card p-8 backdrop-blur-xl bg-surface/90">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-content mb-1.5">{t('common.email')}</label>
              <input type="email" className="input" placeholder="company@example.com"
                value={email} onChange={e => setEmail(e.target.value)} required />
            </div>
            {error && <div className="bg-red-50 border border-red-200 text-red-700 dark:bg-red-500/10 dark:border-red-500/30 dark:text-red-300 text-sm px-4 py-3 rounded-lg">{error}</div>}
            <button type="submit" className="btn-primary w-full justify-center py-2.5" disabled={loading}>
              {loading ? t('login.loading') : t('forgot.submit')}
            </button>
          </form>
          <p className="text-center text-sm text-muted mt-6">
            <Link to="/login" className="text-brand-600 font-medium hover:underline">{t('forgot.backToLogin')}</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
