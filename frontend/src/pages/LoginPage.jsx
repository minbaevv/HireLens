import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import api from '../api/client'
import { Eye, EyeOff } from 'lucide-react'
import { useT } from '../i18n'
import Logo from '../components/Logo'
import LanguageSwitcher from '../components/LanguageSwitcher'
import AnimatedBackground from '../components/AnimatedBackground'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const { t } = useT()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPass, setShowPass] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.append('username', form.email)
      params.append('password', form.password)
      const { data } = await api.post('/auth/login', params)
      login(data.access_token)
      // Сохраняем refresh_token для автоматического обновления
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token)
      }
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || t('login.errorDefault'))
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
          <div className="inline-flex items-center justify-center w-16 h-16 bg-[#0b1e3f] rounded-2xl mb-4 shadow-lg">
            <Logo className="w-10 h-10" title="HireLens" gradId="hl-login" />
          </div>
          <h1 className="page-title">HireLens</h1>
          <p className="page-subtitle">{t('login.subtitle')}</p>
        </div>
        <div className="card p-8 backdrop-blur-xl bg-surface/90">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-content mb-1.5">{t('common.email')}</label>
              <input type="email" className="input" placeholder="company@example.com"
                value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} required />
            </div>
            <div>
              <label className="block text-sm font-medium text-content mb-1.5">{t('login.password')}</label>
              <div className="relative">
                <input type={showPass ? 'text' : 'password'} className="input pr-10" placeholder="••••••••"
                  value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} required />
                <button type="button" onClick={() => setShowPass(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-faint hover:text-muted">
                  {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <div className="text-right -mt-2">
              <Link to="/forgot-password" className="text-sm text-brand-600 hover:underline">{t('login.forgotPassword')}</Link>
            </div>
            {error && <div className="bg-red-50 border border-red-200 text-red-700 dark:bg-red-500/10 dark:border-red-500/30 dark:text-red-300 text-sm px-4 py-3 rounded-lg">{error}</div>}
            <button type="submit" className="btn-primary w-full justify-center py-2.5" disabled={loading}>
              {loading ? t('login.loading') : t('login.submit')}
            </button>
          </form>
          <p className="text-center text-sm text-muted mt-6">
            {t('login.noAccount')}{' '}
            <Link to="/register" className="text-brand-600 font-medium hover:underline">{t('login.registerLink')}</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
