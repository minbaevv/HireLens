import { useEffect, useState, useCallback } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import api from '../api/client'
import ScoreBadge from '../components/ScoreBadge'
import StatusBadge from '../components/StatusBadge'
import RecommendationBadge from '../components/RecommendationBadge'
import { fmtDate } from '../utils/datetime'
import Spinner from '../components/Spinner'
import { SkeletonRows } from '../components/Skeleton'
import { useT } from '../i18n'
import { useAuth } from '../hooks/useAuth'
import {
  Users, Search, Download, ChevronUp, ChevronDown, ChevronLeft, ChevronRight,
  AlertTriangle, Tag, X, Mail, FileSpreadsheet, FileText,
} from 'lucide-react'

const PAGE_SIZE = 20
const DATE_LOCALES = { ru: 'ru-RU', ky: 'ky-KG', en: 'en-US' }
const STATUS_OPTIONS = ['applied', 'interviewing', 'completed', 'invited', 'hired', 'rejected']

const EXPORT_MIME = {
  csv: 'text/csv',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  pdf: 'application/pdf',
}

// Номер для wa.me: местный 0705... и номер без кода страны приводим к 996XXXXXXXXX,
// иначе WhatsApp не находит контакт. Старые записи в базе хранятся без нормализации.
function waPhone(phone) {
  const d = String(phone || '').replace(/\D/g, '')
  if (d.startsWith('996')) return d
  if (d.startsWith('0')) return '996' + d.slice(1)
  if (d.length === 9) return '996' + d
  return d
}

// Аватар кандидата: фото, а если его нет — инициалы на фирменном фоне.
// Раньше строки без фото оставались без аватара и список выглядел рваным.
function Avatar({ name, src, size = 'w-9 h-9' }) {
  if (src) {
    return <img src={src} alt="" className={`${size} rounded-full object-cover border border-line shrink-0`} />
  }
  const initials = String(name || '?').trim().split(/\s+/).slice(0, 2).map(w => w.charAt(0)).join('').toUpperCase()
  return (
    <div className={`${size} rounded-full shrink-0 flex items-center justify-center text-xs font-semibold bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300`}>
      {initials}
    </div>
  )
}

export default function CandidatesPage() {
  const { t, lang } = useT()
  const navigate = useNavigate()
  const { canWrite } = useAuth()
  const [searchParams] = useSearchParams()
  const [data, setData]             = useState({ items: [], total: 0, pages: 1 })
  const [loading, setLoading]       = useState(true)
  const [search, setSearch]         = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [tagFilter, setTagFilter]   = useState('')
  const [reviewOnly, setReviewOnly] = useState(searchParams.get('review') === '1')
  const [sortBy, setSortBy]         = useState('created_at')
  const [order, setOrder]           = useState('desc')
  const [page, setPage]             = useState(1)

  const [availableTags, setAvailableTags] = useState([])
  const [selected, setSelected]     = useState(() => new Set())
  const [bulkStatus, setBulkStatus] = useState('')
  const [bulkNotify, setBulkNotify] = useState(false)
  const [tagInput, setTagInput]     = useState('')
  const [busy, setBusy]             = useState(false)
  const [flash, setFlash]           = useState(null)
  const [exportOpen, setExportOpen] = useState(false)
  const [exporting, setExporting]   = useState(false)

  const fetchCandidates = useCallback(() => {
    setLoading(true)
    const params = { page, page_size: PAGE_SIZE, sort_by: sortBy, order }
    if (search)       params.search = search
    if (statusFilter) params.status = statusFilter
    if (tagFilter)    params.tag = tagFilter
    if (reviewOnly)   params.requires_review = true
    api.get('/candidates', { params })
      .then(r => setData(r.data))
      .finally(() => setLoading(false))
  }, [page, sortBy, order, search, statusFilter, tagFilter, reviewOnly])

  const fetchTags = useCallback(() => {
    api.get('/candidates/tags')
      .then(r => setAvailableTags(Array.isArray(r.data) ? r.data : []))
      .catch(() => {})
  }, [])

  useEffect(() => { fetchCandidates() }, [fetchCandidates])
  useEffect(() => { fetchTags() }, [fetchTags])

  // Сброс на первую страницу при изменении фильтров
  useEffect(() => { setPage(1) }, [search, statusFilter, tagFilter, reviewOnly, sortBy, order])

  // Авто-скрытие флеш-сообщения
  useEffect(() => {
    if (!flash) return
    const id = setTimeout(() => setFlash(null), 4000)
    return () => clearTimeout(id)
  }, [flash])

  function toggleSort(col) {
    if (sortBy === col) setOrder(o => o === 'desc' ? 'asc' : 'desc')
    else { setSortBy(col); setOrder('desc') }
  }

  function SortIcon({ col }) {
    if (sortBy !== col) return null
    return order === 'desc' ? <ChevronDown className="w-3 h-3 inline ml-1" /> : <ChevronUp className="w-3 h-3 inline ml-1" />
  }

  // ---- Выбор строк ----
  const selectedIds = Array.from(selected)
  const pageIds = data.items.map(c => c.id)
  const allOnPageSelected = pageIds.length > 0 && pageIds.every(id => selected.has(id))

  function toggleOne(id) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  function toggleAllOnPage() {
    setSelected(prev => {
      const next = new Set(prev)
      if (allOnPageSelected) pageIds.forEach(id => next.delete(id))
      else pageIds.forEach(id => next.add(id))
      return next
    })
  }

  function clearSelection() { setSelected(new Set()) }

  // ---- Массовые операции ----
  async function applyBulkStatus() {
    if (!selectedIds.length) return
    if (!bulkStatus) { setFlash({ type: 'error', text: t('candidates.bulkPickStatus') }); return }
    setBusy(true)
    try {
      const r = await api.post('/candidates/bulk/status', {
        candidate_ids: selectedIds, status: bulkStatus, notify: bulkNotify,
      })
      setFlash({ type: 'success', text: t('candidates.bulkStatusDone', { count: r.data.updated }) })
      setBulkStatus(''); setBulkNotify(false); clearSelection(); fetchCandidates()
    } catch { setFlash({ type: 'error', text: t('candidates.bulkError') }) }
    finally { setBusy(false) }
  }

  async function bulkTag(mode) {
    if (!selectedIds.length) return
    const value = tagInput.trim()
    if (!value) return
    setBusy(true)
    try {
      const r = await api.post('/candidates/bulk/tags', {
        candidate_ids: selectedIds,
        add: mode === 'add' ? [value] : [],
        remove: mode === 'remove' ? [value] : [],
      })
      setFlash({
        type: 'success',
        text: t(mode === 'add' ? 'candidates.bulkTagAdded' : 'candidates.bulkTagRemoved', { count: r.data.updated }),
      })
      setTagInput(''); fetchCandidates(); fetchTags()
    } catch { setFlash({ type: 'error', text: t('candidates.bulkError') }) }
    finally { setBusy(false) }
  }

  async function notifyBulk() {
    if (!selectedIds.length) return
    setBusy(true)
    try {
      const r = await api.post('/candidates/bulk/notify', { candidate_ids: selectedIds })
      setFlash({ type: 'success', text: t('candidates.bulkNotifyDone', { count: r.data.updated }) })
    } catch { setFlash({ type: 'error', text: t('candidates.bulkError') }) }
    finally { setBusy(false) }
  }

  // ---- Экспорт ----
  async function doExport(format) {
    setExporting(true)
    try {
      const params = { format }
      if (selectedIds.length) {
        params.ids = selectedIds.join(',')
      } else {
        if (search)       params.search = search
        if (statusFilter) params.status = statusFilter
        if (tagFilter)    params.tag = tagFilter
        if (reviewOnly)   params.requires_review = true
      }
      const response = await api.get('/candidates/export', { responseType: 'blob', params })
      const url = window.URL.createObjectURL(new Blob([response.data], { type: EXPORT_MIME[format] }))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `candidates.${format}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch { setFlash({ type: 'error', text: t('candidates.bulkError') }) }
    finally { setExporting(false); setExportOpen(false) }
  }


  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="page-title">{t('nav.candidates')}</h1>
          <p className="page-subtitle">{t('candidates.countSuffix', { count: data.total })}</p>
        </div>
        <div className="relative">
          <button
            onClick={() => setExportOpen(o => !o)}
            disabled={exporting}
            className="btn-secondary flex items-center gap-2 disabled:opacity-50"
          >
            {exporting ? <Spinner className="w-4 h-4" /> : <Download className="w-4 h-4" />}
            {t('candidates.export')}
            <ChevronDown className="w-3.5 h-3.5" />
          </button>
          {exportOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setExportOpen(false)} />
              <div className="absolute right-0 mt-2 w-56 rounded-lg border border-line bg-surface shadow-lg z-20 overflow-hidden">
                <p className="px-3 py-2 text-xs text-faint border-b border-line">
                  {selectedIds.length
                    ? t('candidates.exportSelectedHint', { count: selectedIds.length })
                    : t('candidates.exportAllHint')}
                </p>
                <button onClick={() => doExport('csv')} className="w-full flex items-center gap-2 px-3 py-2 text-sm text-content hover:bg-surface-muted">
                  <FileText className="w-4 h-4 text-muted" /> {t('candidates.exportCsvItem')}
                </button>
                <button onClick={() => doExport('xlsx')} className="w-full flex items-center gap-2 px-3 py-2 text-sm text-content hover:bg-surface-muted">
                  <FileSpreadsheet className="w-4 h-4 text-emerald-600" /> {t('candidates.exportExcel')}
                </button>
                <button onClick={() => doExport('pdf')} className="w-full flex items-center gap-2 px-3 py-2 text-sm text-content hover:bg-surface-muted">
                  <FileText className="w-4 h-4 text-red-500" /> {t('candidates.exportPdf')}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Флеш-сообщение */}
      {flash && (
        <div className={`mb-4 px-4 py-2 rounded-lg text-sm ${
          flash.type === 'error'
            ? 'bg-red-50 text-red-700 border border-red-200 dark:bg-red-500/15 dark:text-red-300 dark:border-red-500/30'
            : 'bg-green-50 text-green-700 border border-green-200 dark:bg-green-500/15 dark:text-green-300 dark:border-green-500/30'
        }`}>
          {flash.text}
        </div>
      )}

      {/* Фильтры */}
      <div className="flex flex-wrap gap-3 mb-6">
        <div className="relative flex-1 min-w-[12rem] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-faint" />
          <input className="input pl-9" placeholder={t('candidates.searchPlaceholder')}
            value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <select className="input w-auto" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="">{t('candidates.allStatuses')}</option>
          {STATUS_OPTIONS.map(s => <option key={s} value={s}>{t(`status.${s}`)}</option>)}
        </select>
        {availableTags.length > 0 && (
          <select className="input w-auto" value={tagFilter} onChange={e => setTagFilter(e.target.value)}>
            <option value="">{t('candidates.allTags')}</option>
            {availableTags.map(tg => <option key={tg} value={tg}>{tg}</option>)}
          </select>
        )}
        <button
          onClick={() => setReviewOnly(v => !v)}
          className={`inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border transition-colors ${
            reviewOnly
              ? 'bg-amber-50 border-amber-300 text-amber-700 dark:bg-amber-500/15 dark:border-amber-500/30 dark:text-amber-300'
              : 'bg-surface border-line text-muted hover:bg-surface-muted'
          }`}
          title={t('candidates.reviewFilterOn')}
        >
          <AlertTriangle className="w-4 h-4" />
          {reviewOnly ? t('candidates.reviewFilterOn') : t('candidates.reviewFilterAll')}
        </button>
      </div>

      {/* Панель массовых действий */}
      {canWrite && selectedIds.length > 0 && (
        <div className="card mb-4 p-4 flex flex-wrap items-center gap-3 border-brand-200 bg-brand-50/40 dark:bg-brand-500/10">
          <span className="text-sm font-semibold text-content">
            {t('candidates.bulkSelected', { count: selectedIds.length })}
          </span>

          {/* Статус */}
          <div className="flex items-center gap-2">
            <select className="input w-auto py-1.5" value={bulkStatus} onChange={e => setBulkStatus(e.target.value)}>
              <option value="">{t('candidates.bulkStatusPlaceholder')}</option>
              {STATUS_OPTIONS.map(s => <option key={s} value={s}>{t(`status.${s}`)}</option>)}
            </select>
            <label className="flex items-center gap-1.5 text-xs text-muted select-none">
              <input type="checkbox" checked={bulkNotify} onChange={e => setBulkNotify(e.target.checked)} />
              {t('candidates.bulkNotifyCheckbox')}
            </label>
            <button onClick={applyBulkStatus} disabled={busy} className="btn-primary py-1.5 px-3 text-sm disabled:opacity-50">
              {t('candidates.bulkApply')}
            </button>
          </div>

          {/* Теги */}
          <div className="flex items-center gap-2">
            <div className="relative">
              <Tag className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-faint" />
              <input
                className="input py-1.5 pl-8 w-40"
                placeholder={t('candidates.bulkTagPlaceholder')}
                value={tagInput}
                onChange={e => setTagInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') bulkTag('add') }}
              />
            </div>
            <button onClick={() => bulkTag('add')} disabled={busy || !tagInput.trim()} className="btn-secondary py-1.5 px-3 text-sm disabled:opacity-50">
              {t('candidates.bulkTagAdd')}
            </button>
            <button onClick={() => bulkTag('remove')} disabled={busy || !tagInput.trim()} className="btn-secondary py-1.5 px-3 text-sm disabled:opacity-50">
              {t('candidates.bulkTagRemove')}
            </button>
          </div>

          {/* Уведомление */}
          <button onClick={notifyBulk} disabled={busy} className="btn-secondary py-1.5 px-3 text-sm flex items-center gap-1.5 disabled:opacity-50">
            <Mail className="w-3.5 h-3.5" /> {t('candidates.bulkNotify')}
          </button>

          <button onClick={clearSelection} className="ml-auto text-sm text-muted hover:text-content flex items-center gap-1">
            <X className="w-3.5 h-3.5" /> {t('candidates.bulkClear')}
          </button>
          {busy && <Spinner className="w-4 h-4" />}
        </div>
      )}

      {loading ? (
        <SkeletonRows rows={6} />
      ) : data.items.length === 0 ? (
        <div className="card py-16 text-center">
          <Users className="w-12 h-12 mx-auto text-faint mb-4" />
          <p className="text-muted">{t('candidates.emptyTitle')}</p>
        </div>
      ) : (
        <>
          <div className="card overflow-hidden mb-4 hidden md:block">
            <table className="w-full">
              <thead>
                <tr className="border-b border-line">
                  {canWrite && (
                    <th className="px-4 py-3 w-10">
                      <input
                        type="checkbox"
                        checked={allOnPageSelected}
                        onChange={toggleAllOnPage}
                        title={t('candidates.bulkSelectAll')}
                      />
                    </th>
                  )}
                  <th className="th-cell">{t('candidates.colCandidate')}</th>
                  <th className="th-cell">{t('candidates.colStatus')}</th>
                  <th
                    className="th-cell cursor-pointer select-none hover:text-content"
                    onClick={() => toggleSort('score')}
                  >{t('candidates.colScore')} <SortIcon col="score" /></th>
                  <th className="th-cell" title={t('candidates.preScreenHint')}>{t('candidates.colPreScreen')}</th>
                  <th className="th-cell">{t('candidates.colRecommendation')}</th>
                  <th
                    className="th-cell cursor-pointer select-none hover:text-content"
                    onClick={() => toggleSort('created_at')}
                  >{t('candidates.colDate')} <SortIcon col="created_at" /></th>
                  <th className="px-6 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data.items.map(c => (
                  <tr key={c.id} onClick={() => navigate(`/candidates/${c.id}`)} className={`hover:bg-surface-muted transition-colors cursor-pointer ${selected.has(c.id) ? 'bg-brand-50/40 dark:bg-brand-500/10' : ''}`}>
                    {canWrite && (
                      <td className="px-4 py-4" onClick={e => e.stopPropagation()}>
                        <input type="checkbox" checked={selected.has(c.id)} onChange={() => toggleOne(c.id)} />
                      </td>
                    )}
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <Avatar name={c.name} src={c.photo_url} />
                        <div>
                          <p className="text-sm font-medium text-content">{c.name}</p>
                          <p className="text-xs text-faint">{c.email}</p>
                          {c.phone && <p className="text-xs text-faint"><a href={`https://wa.me/${waPhone(c.phone)}`} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()} className="hover:text-brand-600 hover:underline">{c.phone}</a></p>}
                          {Array.isArray(c.tags) && c.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1">
                              {c.tags.map(tg => (
                                <span key={tg} className="inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-brand-100 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300">
                                  <Tag className="w-2.5 h-2.5" />{tg}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        {c.requires_manual_review && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">
                            <AlertTriangle className="w-3 h-3" /> {t('candidates.reviewBadge')}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4"><StatusBadge status={c.status} /></td>
                    <td className="px-6 py-4"><ScoreBadge score={c.score} /></td>
                    <td className="px-6 py-4">
                      {c.pre_score != null ? (
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                          c.pre_score >= 70 ? 'bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300' :
                          c.pre_score >= 40 ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-500/15 dark:text-yellow-300' : 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300'
                        }`}>{Math.round(c.pre_score)}</span>
                      ) : <span className="text-xs text-faint">—</span>}
                    </td>
                    <td className="px-6 py-4"><RecommendationBadge value={c.recommendation} /></td>
                    <td className="px-6 py-4 text-xs text-faint">
                      {fmtDate(c.created_at, DATE_LOCALES[lang] || 'ru-RU')}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link to={`/candidates/${c.id}`} className="text-sm text-brand-600 hover:underline font-medium">{t('candidates.viewDetails')}</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Мобильные карточки (на десктопе — таблица выше) */}
          <div className="md:hidden space-y-3 mb-4">
            {data.items.map(c => (
              <Link key={c.id} to={`/candidates/${c.id}`} className="card block p-4 active:bg-surface-muted transition-colors">
                <div className="flex items-start justify-between gap-3">
                  <Avatar name={c.name} src={c.photo_url} size="w-10 h-10" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-content truncate">{c.name}</p>
                    <p className="text-xs text-faint truncate">{c.email}</p>
                    {c.phone && <p className="text-xs text-faint"><a href={`https://wa.me/${waPhone(c.phone)}`} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()} className="hover:text-brand-600 hover:underline">{c.phone}</a></p>}
                  </div>
                  <StatusBadge status={c.status} />
                </div>
                <div className="flex items-center flex-wrap gap-2 mt-3">
                  <ScoreBadge score={c.score} />
                  <RecommendationBadge value={c.recommendation} />
                  {c.requires_manual_review && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">
                      <AlertTriangle className="w-3 h-3" /> {t('candidates.reviewBadge')}
                    </span>
                  )}
                  <span className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-brand-600">
                    {t('candidates.viewDetails')} <ChevronRight className="w-3.5 h-3.5" />
                  </span>
                </div>
                {Array.isArray(c.tags) && c.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {c.tags.map(tg => (
                      <span key={tg} className="inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-brand-100 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300">
                        <Tag className="w-2.5 h-2.5" />{tg}
                      </span>
                    ))}
                  </div>
                )}
              </Link>
            ))}
          </div>

          {/* Пагинация */}
          {data.pages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted">
                {t('candidates.paginationInfo', { page, pages: data.pages, total: data.total })}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="btn-secondary px-3 py-2 disabled:opacity-40"
                ><ChevronLeft className="w-4 h-4" /></button>
                <button
                  onClick={() => setPage(p => Math.min(data.pages, p + 1))}
                  disabled={page === data.pages}
                  className="btn-secondary px-3 py-2 disabled:opacity-40"
                ><ChevronRight className="w-4 h-4" /></button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
