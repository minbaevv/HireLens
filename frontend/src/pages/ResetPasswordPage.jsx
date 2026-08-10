import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import api from '../api/client'
import { useAuth } from '../hooks/useAuth'
import { Eye, EyeOff } from 'lucide-react'
import { useT } from '../i18n'
import Logo from '../components/Logo'
import LanguageSwitcher from '../components/LanguageSwitcher'
import AnimatedBackground from '../components/AnimatedBackground'

export default function ResetPasswordPage() {
  const [params] = useSearchParams()
  const email = params.get('email') || ''
  const navigate = useNavigate()
  const { login } = useAuth()
  const { t } = useT()
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (password !== confirm) {
      setError(t('reset.mismatch'))
      return
    }
    setLoading(true)
    try {
      const { data } = await api.post('/auth/reset-password', { email, code, new_password: password })
      // Сервер сразу возвращает токены (как verify-email) — логиним без повторного ввода пароля.
      login(data.access_token)
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token)
      }
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || t('reset.errorDefault'))
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
            <Logo className="w-10 h-10" title="HireLens" gradId="hl-reset" />
          </div>
          <h1 className="page-title">{t('reset.title')}</h1>
          <p className="page-subtitle">{t('reset.subtitle')} <span className="font-medium text-content">{email}</span></p>
        </div>
        <div className="card p-8 backdrop-blur-xl bg-surface/90">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-content mb-1.5">{t('reset.codeLabel')}</label>
              <input type="text" inputMode="numeric" autoFocus maxLength={6}
                className="input w-full text-center text-2xl tracking-[0.5em] font-mono" placeholder="000000"
                value={code} onChange={e => setCode(e.target.value.replace(/\D/g, ''))} required />
            </div>
            <div>
              <label className="block text-sm font-medium text-content mb-1.5">{t('reset.newPassword')}</label>
              <div className="relative">
                <input type={showPass ? 'text' : 'password'} className="input pr-10" placeholder="••••••••"
                  value={password} onChange={e => setPassword(e.target.value)} minLength={6} required />
                <button type="button" onClick={() => setShowPass(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-faint hover:text-muted">
                  {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-content mb-1.5">{t('reset.confirmPassword')}</label>
              <input type={showPass ? 'text' : 'password'} className="input" placeholder="••••••••"
                value={confirm} onChange={e => setConfirm(e.target.value)} minLength={6} required />
            </div>
            {error && <div className="bg-red-50 border border-red-200 text-red-700 dark:bg-red-500/10 dark:border-red-500/30 dark:text-red-300 text-sm px-4 py-3 rounded-lg">{error}</div>}
            <button type="submit" className="btn-primary w-full justify-center py-2.5" disabled={loading || code.length < 6}>
              {loading ? t('login.loading') : t('reset.submit')}
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
