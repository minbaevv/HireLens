import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import api from '../api/client'
import { Bot, Eye, EyeOff } from 'lucide-react'
import { useT } from '../i18n'
import LanguageSwitcher from '../components/LanguageSwitcher'
import AnimatedBackground from '../components/AnimatedBackground'

export default function RegisterPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const { t } = useT()
  const [form, setForm] = useState({ email: '', password: '', company_name: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPass, setShowPass] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.post('/auth/register', form)
      navigate(`/verify-email?email=${encodeURIComponent(form.email)}`)
    } catch (err) {
      setError(err.response?.data?.detail || t('register.errorDefault'))
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
          <div className="inline-flex items-center justify-center w-16 h-16 bg-brand-600 rounded-2xl mb-4 shadow-lg">
            <Bot className="w-8 h-8 text-white" />
          </div>
          <h1 className="page-title">{t('register.title')}</h1>
          <p className="page-subtitle">{t('register.subtitle')}</p>
        </div>
        <div className="card p-8 backdrop-blur-xl bg-surface/90">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-content mb-1.5">{t('register.companyName')}</label>
              <input type="text" className="input" placeholder={t('register.companyPlaceholder')}
                value={form.company_name} onChange={e => setForm(f => ({ ...f, company_name: e.target.value }))} required />
            </div>
            <div>
              <label className="block text-sm font-medium text-content mb-1.5">{t('common.email')}</label>
              <input type="email" className="input" placeholder="hr@company.com"
                value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} required />
            </div>
            <div>
              <label className="block text-sm font-medium text-content mb-1.5">{t('register.password')}</label>
              <div className="relative">
                <input type={showPass ? 'text' : 'password'} className="input pr-10" placeholder={t('register.passwordPlaceholder')}
                  value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} minLength={6} required />
                <button type="button" onClick={() => setShowPass(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-faint hover:text-muted">
                  {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            {error && <div className="bg-red-50 border border-red-200 text-red-700 dark:bg-red-500/10 dark:border-red-500/30 dark:text-red-300 text-sm px-4 py-3 rounded-lg">{error}</div>}
            <button type="submit" className="btn-primary w-full justify-center py-2.5" disabled={loading}>
              {loading ? t('register.loading') : t('register.submit')}
            </button>
          </form>
          <p className="text-center text-sm text-muted mt-6">
            {t('register.hasAccount')}{' '}
            <Link to="/login" className="text-brand-600 font-medium hover:underline">{t('register.loginLink')}</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
