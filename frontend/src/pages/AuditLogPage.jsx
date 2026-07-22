import { useEffect, useState, useCallback } from 'react'
import { ScrollText, RefreshCw, ChevronLeft, ChevronRight, Filter, X } from 'lucide-react'
import api from '../api/client'
import { useT } from '../i18n'

const PAGE_SIZE = 100
const DATE_LOCALES = { ru: 'ru-RU', ky: 'ky-KG', en: 'en-US' }

function fmtDate(iso, locale) {
  if (!iso) return '\u2014'
  try {
    return new Date(iso).toLocaleString(locale || 'ru-RU', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function prettyDetail(detail) {
  if (!detail) return ''
  try {
    return JSON.stringify(JSON.parse(detail), null, 2)
  } catch {
    return detail
  }
}

export default function AuditLogPage() {
  const { t, lang } = useT()
  const locale = DATE_LOCALES[lang] || 'ru-RU'

  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(0)
  const [expanded, setExpanded] = useState(null)

  // применённые фильтры
  const [action, setAction] = useState('')
  const [entityType, setEntityType] = useState('')
  // черновики фильтров (поля ввода)
  const [actionDraft, setActionDraft] = useState('')
  const [entityDraft, setEntityDraft] = useState('')

  const fetchLogs = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = { limit: PAGE_SIZE, offset: page * PAGE_SIZE }
      if (action) params.action = action
      if (entityType) params.entity_type = entityType
      const { data } = await api.get('/analytics/audit-logs', { params })
      setRows(Array.isArray(data) ? data : [])
    } catch {
      setError(t('audit.error'))
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [page, action, entityType, t])

  useEffect(() => { fetchLogs() }, [fetchLogs])

  const applyFilters = () => {
    setAction(actionDraft.trim())
    setEntityType(entityDraft.trim())
    setPage(0)
    setExpanded(null)
  }
  const resetFilters = () => {
    setActionDraft('')
    setEntityDraft('')
    setAction('')
    setEntityType('')
    setPage(0)
    setExpanded(null)
  }

  const actorLabel = (r) => {
    const type = r.actor_type === 'team_member'
      ? t('audit.actorTeamMember')
      : r.actor_type === 'company'
        ? t('audit.actorCompany')
        : t('audit.actorUnknown')
    return r.actor_email ? `${r.actor_email} \u00b7 ${type}` : type
  }

  const entityLabel = (r) => {
    if (!r.entity_type) return '\u2014'
    return r.entity_id ? `${r.entity_type} #${r.entity_id}` : r.entity_type
  }

  const hasFilters = Boolean(action || entityType)

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ScrollText className="w-6 h-6 text-content" />
        <div>
          <h1 className="text-xl font-semibold text-content">{t('audit.title')}</h1>
          <p className="text-sm text-muted">{t('audit.subtitle')}</p>
        </div>
      </div>

      <div className="card p-4 flex flex-wrap items-center gap-3">
        <Filter className="w-4 h-4 text-faint" />
        <input
          className="input flex-1 min-w-[200px]"
          placeholder={t('audit.filterAction')}
          value={actionDraft}
          onChange={(e) => setActionDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') applyFilters() }}
        />
        <input
          className="input flex-1 min-w-[200px]"
          placeholder={t('audit.filterEntity')}
          value={entityDraft}
          onChange={(e) => setEntityDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') applyFilters() }}
        />
        <button className="btn-secondary" onClick={applyFilters}>{t('audit.apply')}</button>
        {hasFilters && (
          <button className="btn-secondary inline-flex items-center gap-1" onClick={resetFilters}>
            <X className="w-4 h-4" />{t('audit.reset')}
          </button>
        )}
        <button className="btn-secondary inline-flex items-center gap-1" onClick={fetchLogs} disabled={loading}>
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />{t('audit.refresh')}
        </button>
      </div>

      {error && (
        <div className="card p-4 text-sm text-red-600 dark:text-red-300">{error}</div>
      )}

      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-line">
              <th className="text-left text-xs font-semibold text-muted uppercase tracking-wide px-6 py-3 whitespace-nowrap">{t('audit.colDate')}</th>
              <th className="text-left text-xs font-semibold text-muted uppercase tracking-wide px-6 py-3">{t('audit.colAction')}</th>
              <th className="text-left text-xs font-semibold text-muted uppercase tracking-wide px-6 py-3">{t('audit.colActor')}</th>
              <th className="text-left text-xs font-semibold text-muted uppercase tracking-wide px-6 py-3">{t('audit.colEntity')}</th>
              <th className="text-left text-xs font-semibold text-muted uppercase tracking-wide px-6 py-3">{t('audit.colIp')}</th>
              <th className="text-left text-xs font-semibold text-muted uppercase tracking-wide px-6 py-3">{t('audit.colDetail')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {loading && rows.length === 0 ? (
              <tr><td colSpan={6} className="px-6 py-8 text-center text-muted">{t('audit.loading')}</td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={6} className="px-6 py-8 text-center text-muted">{t('audit.empty')}</td></tr>
            ) : (
              rows.map((r) => (
                <tr key={r.id} className="align-top">
                  <td className="px-6 py-3 text-sm text-muted whitespace-nowrap">{fmtDate(r.created_at, locale)}</td>
                  <td className="px-6 py-3">
                    <code className="text-xs bg-surface-muted px-1.5 py-0.5 rounded text-content">{r.action}</code>
                  </td>
                  <td className="px-6 py-3 text-sm text-content">{actorLabel(r)}</td>
                  <td className="px-6 py-3 text-sm text-muted whitespace-nowrap">{entityLabel(r)}</td>
                  <td className="px-6 py-3 text-sm text-faint whitespace-nowrap">{r.ip_address || '\u2014'}</td>
                  <td className="px-6 py-3">
                    {r.detail ? (
                      <div>
                        <button
                          className="text-xs text-brand-600 hover:underline"
                          onClick={() => setExpanded(expanded === r.id ? null : r.id)}
                        >
                          {expanded === r.id ? t('audit.hideDetail') : t('audit.viewDetail')}
                        </button>
                        {expanded === r.id && (
                          <pre className="mt-2 max-w-md overflow-x-auto whitespace-pre-wrap break-words text-xs text-muted bg-surface-muted p-2 rounded">{prettyDetail(r.detail)}</pre>
                        )}
                      </div>
                    ) : (
                      <span className="text-faint">\u2014</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm text-muted">{t('audit.pageInfo', { page: page + 1 })}</span>
        <div className="flex items-center gap-2">
          <button
            className="btn-secondary inline-flex items-center gap-1"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0 || loading}
          >
            <ChevronLeft className="w-4 h-4" />{t('audit.prev')}
          </button>
          <button
            className="btn-secondary inline-flex items-center gap-1"
            onClick={() => setPage((p) => p + 1)}
            disabled={rows.length < PAGE_SIZE || loading}
          >
            {t('audit.next')}<ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
