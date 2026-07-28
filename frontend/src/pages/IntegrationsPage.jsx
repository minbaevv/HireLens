import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Plug, KeyRound, Webhook, Trash2, Plus, Copy, Check, Send, Power, CalendarClock } from 'lucide-react'
import api from '../api/client'
import Spinner from '../components/Spinner'
import { useT } from '../i18n'
import { fmtDateTime } from '../utils/datetime'

function CopyField({ value, t }) {
  const [copied, setCopied] = useState(false)
  return (
    <div className="flex items-center gap-2">
      <code className="flex-1 bg-surface-muted text-content px-3 py-2 rounded-lg text-sm font-mono break-all select-all">{value}</code>
      <button
        type="button"
        onClick={() => {
          navigator.clipboard?.writeText(value)
          setCopied(true)
          setTimeout(() => setCopied(false), 1500)
        }}
        className="btn-secondary shrink-0 inline-flex items-center gap-1"
      >
        {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
        {copied ? t('integrations.copied') : t('integrations.copy')}
      </button>
    </div>
  )
}

export default function IntegrationsPage() {
  const { t } = useT()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [searchParams, setSearchParams] = useSearchParams()

  // Google Calendar
  const [google, setGoogle] = useState(null)
  const [googleBusy, setGoogleBusy] = useState(false)

  // API keys
  const [keys, setKeys] = useState([])
  const [keyName, setKeyName] = useState('')
  const [creatingKey, setCreatingKey] = useState(false)
  const [newKey, setNewKey] = useState('')

  // Webhooks
  const [hooks, setHooks] = useState([])
  const [supportedEvents, setSupportedEvents] = useState([])
  const [hookUrl, setHookUrl] = useState('')
  const [hookEvents, setHookEvents] = useState(['*'])
  const [creatingHook, setCreatingHook] = useState(false)
  const [newSecret, setNewSecret] = useState('')

  function handleErr(err, fallback) {
    if (err.response?.status === 403) setError(t('integrations.forbidden'))
    else setError(err.response?.data?.detail || fallback)
  }

  async function load() {
    setLoading(true)
    try {
      const [k, w, ev, g] = await Promise.all([
        api.get('/integrations/api-keys'),
        api.get('/integrations/webhooks'),
        api.get('/integrations/webhooks/events'),
        api.get('/integrations/google/status'),
      ])
      setKeys(k.data)
      setHooks(w.data)
      setSupportedEvents(ev.data)
      setGoogle(g.data)
    } catch (err) {
      handleErr(err, t('integrations.errorLoad'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    const g = searchParams.get('google')
    if (g === 'connected') {
      setNotice(t('integrations.googleConnected'))
      searchParams.delete('google'); setSearchParams(searchParams, { replace: true })
    } else if (g === 'error') {
      setError(t('integrations.googleError'))
      searchParams.delete('google'); setSearchParams(searchParams, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function connectGoogle() {
    setError(''); setNotice('')
    setGoogleBusy(true)
    try {
      const { data } = await api.get('/integrations/google/authorize')
      window.location.href = data.url
    } catch (err) {
      handleErr(err, t('integrations.googleError'))
      setGoogleBusy(false)
    }
  }

  async function disconnectGoogle() {
    if (!window.confirm(t('integrations.googleDisconnectConfirm'))) return
    setError('')
    setGoogleBusy(true)
    try {
      await api.post('/integrations/google/disconnect')
      await load()
    } catch (err) {
      handleErr(err, t('integrations.errorSave'))
    } finally {
      setGoogleBusy(false)
    }
  }

  async function createKey(e) {
    e.preventDefault()
    setError(''); setNotice(''); setNewKey('')
    setCreatingKey(true)
    try {
      const { data } = await api.post('/integrations/api-keys', { name: keyName || 'API key' })
      setNewKey(data.key)
      setKeyName('')
      load()
    } catch (err) {
      handleErr(err, t('integrations.errorSave'))
    } finally {
      setCreatingKey(false)
    }
  }

  async function revokeKey(id) {
    if (!window.confirm(t('integrations.revokeConfirm'))) return
    setError('')
    try {
      await api.delete(`/integrations/api-keys/${id}`)
      load()
    } catch (err) {
      handleErr(err, t('integrations.errorSave'))
    }
  }

  function toggleEvent(ev) {
    setHookEvents(prev => {
      if (ev === '*') return ['*']
      const without = prev.filter(x => x !== '*')
      return without.includes(ev) ? without.filter(x => x !== ev) : [...without, ev]
    })
  }

  async function createHook(e) {
    e.preventDefault()
    setError(''); setNotice(''); setNewSecret('')
    setCreatingHook(true)
    try {
      const { data } = await api.post('/integrations/webhooks', { url: hookUrl, events: hookEvents })
      setNewSecret(data.secret)
      setHookUrl('')
      setHookEvents(['*'])
      load()
    } catch (err) {
      handleErr(err, t('integrations.errorSave'))
    } finally {
      setCreatingHook(false)
    }
  }

  async function toggleHook(hook) {
    setError('')
    try {
      await api.patch(`/integrations/webhooks/${hook.id}`, { is_active: !hook.is_active })
      load()
    } catch (err) {
      handleErr(err, t('integrations.errorSave'))
    }
  }

  async function deleteHook(id) {
    if (!window.confirm(t('integrations.deleteConfirm'))) return
    setError('')
    try {
      await api.delete(`/integrations/webhooks/${id}`)
      load()
    } catch (err) {
      handleErr(err, t('integrations.errorSave'))
    }
  }

  async function testHook(id) {
    setError(''); setNotice('')
    try {
      const { data } = await api.post(`/integrations/webhooks/${id}/test`)
      setNotice(data.success ? t('integrations.testOk') : `${t('integrations.testFail')} (${data.status_code || data.error || '-'})`)
      load()
    } catch (err) {
      handleErr(err, t('integrations.testFail'))
    }
  }

  return (
    <div className="px-8 py-8 max-w-5xl">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300 flex items-center justify-center">
          <Plug className="w-5 h-5" />
        </div>
        <div>
          <h1 className="page-title">{t('integrations.title')}</h1>
          <p className="text-sm text-muted">{t('integrations.subtitle')}</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 dark:bg-red-500/10 dark:border-red-500/30 dark:text-red-300 text-sm px-4 py-3 rounded-lg">{error}</div>
      )}
      {notice && (
        <div className="mb-4 bg-green-50 border border-green-200 text-green-700 dark:bg-green-500/10 dark:border-green-500/30 dark:text-green-300 text-sm px-4 py-3 rounded-lg">{notice}</div>
      )}

      {/* GOOGLE CALENDAR */}
      <div className="card p-6 mb-6">
        <div className="flex items-center gap-2 mb-2">
          <CalendarClock className="w-4 h-4 text-brand-600" />
          <h2 className="text-sm font-semibold text-content">{t('integrations.googleTitle')}</h2>
        </div>
        <p className="text-sm text-muted mb-4">{t('integrations.googleDesc')}</p>

        {!google?.enabled && (
          <p className="text-sm text-muted">{t('integrations.googleNotConfigured')}</p>
        )}

        {google?.enabled && !google?.connected && (
          <button type="button" onClick={connectGoogle} disabled={googleBusy} className="btn-primary inline-flex items-center gap-1">
            {googleBusy ? <Spinner size="sm" /> : <><CalendarClock className="w-4 h-4" /> {t('integrations.googleConnect')}</>}
          </button>
        )}

        {google?.enabled && google?.connected && (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-sm text-content">
              <span className="text-muted">{t('integrations.googleConnectedAs')}: </span>
              <span className="font-medium">{google.email || '—'}</span>
            </div>
            <button type="button" onClick={disconnectGoogle} disabled={googleBusy} className="btn-secondary inline-flex items-center gap-1">
              <Power className="w-4 h-4" /> {t('integrations.googleDisconnect')}
            </button>
          </div>
        )}
      </div>

      {/* API KEYS */}
      <div className="card p-6 mb-6">
        <div className="flex items-center gap-2 mb-2">
          <KeyRound className="w-4 h-4 text-brand-600" />
          <h2 className="text-sm font-semibold text-content">{t('integrations.apiKeysTitle')}</h2>
        </div>
        <p className="text-sm text-muted mb-4">{t('integrations.apiKeysDesc')}</p>

        <form onSubmit={createKey} className="flex flex-col sm:flex-row gap-3 mb-4">
          <input
            className="input flex-1" placeholder={t('integrations.keyNamePlaceholder')}
            value={keyName} onChange={e => setKeyName(e.target.value)}
          />
          <button type="submit" className="btn-primary justify-center inline-flex items-center gap-1" disabled={creatingKey}>
            {creatingKey ? <Spinner size="sm" /> : <><Plus className="w-4 h-4" /> {t('integrations.createKey')}</>}
          </button>
        </form>

        {newKey && (
          <div className="mb-4 bg-amber-50 border border-amber-200 dark:bg-amber-500/10 dark:border-amber-500/30 rounded-lg p-3">
            <p className="text-xs font-medium text-amber-800 dark:text-amber-300 mb-2">{t('integrations.keyShownOnce')}</p>
            <CopyField value={newKey} t={t} />
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-6"><Spinner /></div>
        ) : keys.length === 0 ? (
          <p className="text-sm text-muted text-center py-6">{t('integrations.noKeys')}</p>
        ) : (
          <ul className="divide-y divide-line">
            {keys.map(k => (
              <li key={k.id} className="flex items-center justify-between py-3 gap-4">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-content truncate">
                    {k.name}
                    {k.revoked && <span className="ml-2 text-xs text-red-500">· {t('integrations.revoked')}</span>}
                  </p>
                  <p className="text-xs text-faint font-mono">{k.prefix}… · {t('integrations.lastUsed')}: {k.last_used_at ? fmtDateTime(k.last_used_at) : t('integrations.never')}</p>
                </div>
                {!k.revoked && (
                  <button onClick={() => revokeKey(k.id)} className="btn-secondary shrink-0 inline-flex items-center gap-1 text-red-600">
                    <Trash2 className="w-4 h-4" /> {t('integrations.revoke')}
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* WEBHOOKS */}
      <div className="card p-6">
        <div className="flex items-center gap-2 mb-2">
          <Webhook className="w-4 h-4 text-brand-600" />
          <h2 className="text-sm font-semibold text-content">{t('integrations.webhooksTitle')}</h2>
        </div>
        <p className="text-sm text-muted mb-4">{t('integrations.webhooksDesc')}</p>

        <form onSubmit={createHook} className="space-y-3 mb-4">
          <input
            type="url" className="input w-full" placeholder={t('integrations.urlPlaceholder')} required
            value={hookUrl} onChange={e => setHookUrl(e.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => toggleEvent('*')}
              className={`badge-status cursor-pointer ${hookEvents.includes('*') ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300' : 'bg-surface-muted text-muted'}`}>
              {t('integrations.allEvents')}
            </button>
            {supportedEvents.map(ev => (
              <button key={ev} type="button" onClick={() => toggleEvent(ev)}
                className={`badge-status cursor-pointer font-mono ${hookEvents.includes(ev) ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300' : 'bg-surface-muted text-muted'}`}>
                {ev}
              </button>
            ))}
          </div>
          <button type="submit" className="btn-primary justify-center inline-flex items-center gap-1" disabled={creatingHook}>
            {creatingHook ? <Spinner size="sm" /> : <><Plus className="w-4 h-4" /> {t('integrations.addWebhook')}</>}
          </button>
        </form>

        {newSecret && (
          <div className="mb-4 bg-amber-50 border border-amber-200 dark:bg-amber-500/10 dark:border-amber-500/30 rounded-lg p-3">
            <p className="text-xs font-medium text-amber-800 dark:text-amber-300 mb-2">{t('integrations.secretShownOnce')}</p>
            <CopyField value={newSecret} t={t} />
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-6"><Spinner /></div>
        ) : hooks.length === 0 ? (
          <p className="text-sm text-muted text-center py-6">{t('integrations.noWebhooks')}</p>
        ) : (
          <ul className="divide-y divide-line">
            {hooks.map(h => (
              <li key={h.id} className="py-3">
                <div className="flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-content truncate">{h.url}</p>
                    <p className="text-xs text-faint">
                      {(h.events || []).join(', ')}
                      {' · '}
                      <span className={h.is_active ? 'text-green-600' : 'text-faint'}>
                        {h.is_active ? t('integrations.active') : t('integrations.inactive')}
                      </span>
                      {h.last_status != null && ` · ${t('integrations.lastStatus')}: ${h.last_status}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button onClick={() => testHook(h.id)} className="btn-secondary inline-flex items-center gap-1">
                      <Send className="w-4 h-4" /> {t('integrations.test')}
                    </button>
                    <button onClick={() => toggleHook(h)} className="btn-secondary inline-flex items-center gap-1">
                      <Power className="w-4 h-4" /> {h.is_active ? t('integrations.disable') : t('integrations.enable')}
                    </button>
                    <button onClick={() => deleteHook(h.id)} className="btn-secondary inline-flex items-center gap-1 text-red-600">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
