import { useState, useEffect } from 'react'
import { UserCog, UserPlus, Trash2, ShieldCheck, Crown, Send } from 'lucide-react'
import api from '../api/client'
import Spinner from '../components/Spinner'
import { useAuth } from '../hooks/useAuth'
import { useT } from '../i18n'

const ROLES = ['admin', 'recruiter', 'viewer']

function roleLabel(t, role) {
  return t(`team.role${role.charAt(0).toUpperCase()}${role.slice(1)}`)
}

const ROLE_CLASSES = {
  admin: 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300',
  recruiter: 'bg-blue-100 text-blue-800 dark:bg-blue-500/15 dark:text-blue-300',
  viewer: 'bg-surface-muted text-muted',
}

export default function TeamPage() {
  const { t } = useT()
  const { company } = useAuth()
  const [members, setMembers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [form, setForm] = useState({ name: '', email: '', role: 'recruiter' })
  const [inviting, setInviting] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const { data } = await api.get('/team')
      setMembers(data)
    } catch {
      setError(t('team.errorLoad'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function invite(e) {
    e.preventDefault()
    setError('')
    setNotice('')
    setInviting(true)
    try {
      await api.post('/team/invite', form)
      setNotice(t('team.inviteSent', { email: form.email }))
      setForm({ name: '', email: '', role: 'recruiter' })
      load()
    } catch (err) {
      setError(err.response?.status === 403 ? t('team.forbidden') : (err.response?.data?.detail || t('team.errorInvite')))
    } finally {
      setInviting(false)
    }
  }

  async function changeRole(id, role) {
    setError('')
    try {
      await api.patch(`/team/${id}/role`, { role })
      setMembers(prev => prev.map(m => (m.id === id ? { ...m, role } : m)))
    } catch (err) {
      setError(err.response?.status === 403 ? t('team.forbidden') : (err.response?.data?.detail || t('team.errorLoad')))
    }
  }

  async function remove(member) {
    if (!window.confirm(t('team.removeConfirm', { name: member.name }))) return
    setError('')
    try {
      await api.delete(`/team/${member.id}`)
      setMembers(prev => prev.filter(m => m.id !== member.id))
    } catch (err) {
      setError(err.response?.status === 403 ? t('team.forbidden') : (err.response?.data?.detail || t('team.errorLoad')))
    }
  }

  return (
    <div className="px-8 py-8 max-w-5xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300 flex items-center justify-center">
          <UserCog className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-content">{t('team.title')}</h1>
          <p className="text-sm text-muted">{t('team.subtitle')}</p>
        </div>
      </div>

      {/* Telegram HR-уведомления (per-company) */}
      {company && (
        <div className="card p-6 mb-6">
          <div className="flex items-center gap-2 mb-2">
            <Send className="w-4 h-4 text-brand-600" />
            <h2 className="text-sm font-semibold text-content">{t('team.telegramTitle')}</h2>
          </div>
          <p className="text-sm text-muted mb-3">{t('team.telegramDesc')}</p>
          {company.telegram_chat_id ? (
            <div className="inline-flex items-center gap-2 text-sm text-green-700 dark:text-green-300 bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/30 px-3 py-2 rounded-lg">
              <ShieldCheck className="w-4 h-4" /> {t('team.telegramLinked')}
            </div>
          ) : company.telegram_link_code ? (
            <div>
              <p className="text-sm text-content mb-2">{t('team.telegramInstruction')}</p>
              {company.telegram_bot_username && (
                <a href={`https://t.me/${company.telegram_bot_username}?start=${company.telegram_link_code}`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 transition-colors mb-2">
                  <Send className="w-4 h-4" /> {t('team.telegramConnectBtn')}
                </a>
              )}
              <code className="block bg-surface-muted text-content px-3 py-2 rounded-lg text-sm font-mono select-all">/start {company.telegram_link_code}</code>
            </div>
          ) : null}
        </div>
      )}

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 dark:bg-red-500/10 dark:border-red-500/30 dark:text-red-300 text-sm px-4 py-3 rounded-lg">{error}</div>
      )}
      {notice && (
        <div className="mb-4 bg-green-50 border border-green-200 text-green-700 dark:bg-green-500/10 dark:border-green-500/30 dark:text-green-300 text-sm px-4 py-3 rounded-lg">{notice}</div>
      )}

      {/* Invite form */}
      <div className="card p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <UserPlus className="w-4 h-4 text-brand-600" />
          <h2 className="text-sm font-semibold text-content">{t('team.inviteTitle')}</h2>
        </div>
        <form onSubmit={invite} className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <input
            className="input" placeholder={t('team.name')} required
            value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
          />
          <input
            type="email" className="input" placeholder={t('team.email')} required
            value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
          />
          <select
            className="input"
            value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
          >
            {ROLES.map(r => <option key={r} value={r}>{roleLabel(t, r)}</option>)}
          </select>
          <button type="submit" className="btn-primary justify-center" disabled={inviting}>
            {inviting ? <Spinner size="sm" /> : t('team.sendInvite')}
          </button>
        </form>
      </div>

      {/* Members */}
      <div className="card overflow-hidden">
        <div className="px-6 py-4 border-b border-line">
          <h2 className="text-sm font-semibold text-content">{t('team.members')}</h2>
        </div>

        {/* Owner */}
        {company && (
          <div className="flex items-center justify-between px-6 py-4 border-b border-line">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300 flex items-center justify-center">
                <Crown className="w-4 h-4" />
              </div>
              <div>
                <p className="text-sm font-medium text-content">{company.name} <span className="text-faint">· {t('team.you')}</span></p>
                <p className="text-xs text-faint">{company.email}</p>
              </div>
            </div>
            <span className={`badge-status ${ROLE_CLASSES.admin} inline-flex items-center gap-1`}>
              <Crown className="w-3 h-3" /> {t('team.owner')}
            </span>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-10"><Spinner /></div>
        ) : members.length === 0 ? (
          <p className="text-sm text-muted text-center py-10">{t('team.noMembers')}</p>
        ) : (
          <ul className="divide-y divide-line">
            {members.map(m => (
              <li key={m.id} className="flex items-center justify-between px-6 py-4 gap-4">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-content truncate">{m.name}</p>
                  <p className="text-xs text-faint truncate">{m.email}</p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className={`badge-status inline-flex items-center gap-1 ${m.is_active ? 'bg-green-100 text-green-800 dark:bg-green-500/15 dark:text-green-300' : 'bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300'}`}>
                    {m.is_active ? <ShieldCheck className="w-3 h-3" /> : null}
                    {m.is_active ? t('team.active') : t('team.pending')}
                  </span>
                  <select
                    className="input py-1.5 text-sm w-auto"
                    value={m.role}
                    onChange={e => changeRole(m.id, e.target.value)}
                  >
                    {ROLES.map(r => <option key={r} value={r}>{roleLabel(t, r)}</option>)}
                  </select>
                  <button
                    onClick={() => remove(m)}
                    title={t('team.remove')}
                    className="p-2 rounded-lg text-faint hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/15 dark:hover:text-red-400 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
