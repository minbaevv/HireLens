import { useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import api from '../api/client'
import { useAuth } from '../hooks/useAuth'
import { useT } from '../i18n'
import Logo from '../components/Logo'
import LanguageSwitcher from '../components/LanguageSwitcher'

export default function AcceptInvitePage() {
  const { t } = useT()
  const { login } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const token = params.get('token')

  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await api.post('/team/accept-invite', { token, password })
      login(data.access_token)
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token)
      }
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || t('accept.error'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 to-brand-100 dark:from-slate-900 dark:to-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="flex justify-end mb-2">
          <LanguageSwitcher />
        </div>
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-[#0b1e3f] rounded-2xl mb-4 shadow-lg">
            <Logo className="w-10 h-10" title="HireLens" gradId="hl-accept" />
          </div>
          <h1 className="text-2xl font-bold text-content">{t('accept.title')}</h1>
          <p className="text-muted mt-1">{t('accept.subtitle')}</p>
        </div>
        <div className="card p-8">
          {!token ? (
            <div className="bg-red-50 border border-red-200 text-red-700 dark:bg-red-500/10 dark:border-red-500/30 dark:text-red-300 text-sm px-4 py-3 rounded-lg">
              {t('accept.noToken')}
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-content mb-1.5">{t('accept.password')}</label>
                <div className="relative">
                  <input
                    type={showPass ? 'text' : 'password'} className="input pr-10" placeholder="••••••••"
                    minLength={8} required
                    value={password} onChange={e => setPassword(e.target.value)}
                  />
                  <button type="button" onClick={() => setShowPass(v => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-faint hover:text-muted">
                    {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <p className="text-xs text-faint mt-1.5">{t('accept.passwordHint')}</p>
              </div>
              {error && <div className="bg-red-50 border border-red-200 text-red-700 dark:bg-red-500/10 dark:border-red-500/30 dark:text-red-300 text-sm px-4 py-3 rounded-lg">{error}</div>}
              <button type="submit" className="btn-primary w-full justify-center py-2.5" disabled={loading}>
                {loading ? t('accept.loading') : t('accept.submit')}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
