import { useEffect, useState, useCallback } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import api from '../api/client'
import ScoreBadge from '../components/ScoreBadge'
import StatusBadge from '../components/StatusBadge'
import RecommendationBadge from '../components/RecommendationBadge'
import { fmtDate } from '../utils/datetime'
import Spinner from '../components/Spinner'
import { useT } from '../i18n'
import { Users, Search, Download, ChevronUp, ChevronDown, ChevronLeft, ChevronRight, AlertTriangle } from 'lucide-react'

const PAGE_SIZE = 20
const DATE_LOCALES = { ru: 'ru-RU', ky: 'ky-KG', en: 'en-US' }

export default function CandidatesPage() {
  const { t, lang } = useT()
  const [searchParams] = useSearchParams()
  const [data, setData]             = useState({ items: [], total: 0, pages: 1 })
  const [loading, setLoading]       = useState(true)
  const [search, setSearch]         = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [reviewOnly, setReviewOnly] = useState(searchParams.get('review') === '1')
  const [sortBy, setSortBy]         = useState('created_at')
  const [order, setOrder]           = useState('desc')
  const [page, setPage]             = useState(1)

  const fetchCandidates = useCallback(() => {
    setLoading(true)
    const params = { page, page_size: PAGE_SIZE, sort_by: sortBy, order }
    if (search)       params.search = search
    if (statusFilter) params.status = statusFilter
    if (reviewOnly)   params.requires_review = true
    api.get('/candidates', { params })
      .then(r => setData(r.data))
      .finally(() => setLoading(false))
  }, [page, sortBy, order, search, statusFilter, reviewOnly])

  useEffect(() => { fetchCandidates() }, [fetchCandidates])

  // Сброс на первую страницу при изменении фильтров
  useEffect(() => { setPage(1) }, [search, statusFilter, reviewOnly, sortBy, order])

  function toggleSort(col) {
    if (sortBy === col) setOrder(o => o === 'desc' ? 'asc' : 'desc')
    else { setSortBy(col); setOrder('desc') }
  }

  function SortIcon({ col }) {
    if (sortBy !== col) return null
    return order === 'desc' ? <ChevronDown className="w-3 h-3 inline ml-1" /> : <ChevronUp className="w-3 h-3 inline ml-1" />
  }

  async function exportCsv() {
    const params = {}
    if (search)       params.search = search
    if (statusFilter) params.status = statusFilter
    const response = await api.get('/candidates/export', { responseType: 'blob', params })
    const url = window.URL.createObjectURL(new Blob([response.data], { type: 'text/csv' }))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'candidates.csv')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  }

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-content">{t('nav.candidates')}</h1>
          <p className="text-muted mt-1">{t('candidates.countSuffix', { count: data.total })}</p>
        </div>
        <button onClick={exportCsv} className="btn-secondary flex items-center gap-2">
          <Download className="w-4 h-4" /> {t('candidates.exportCsv')}
        </button>
      </div>

      {/* Фильтры */}
      <div className="flex gap-3 mb-6">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-faint" />
          <input className="input pl-9" placeholder={t('candidates.searchPlaceholder')}
            value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <select className="input w-auto" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="">{t('candidates.allStatuses')}</option>
          <option value="applied">{t('status.applied')}</option>
          <option value="interviewing">{t('status.interviewing')}</option>
          <option value="completed">{t('status.completed')}</option>
          <option value="hired">{t('status.hired')}</option>
          <option value="rejected">{t('status.rejected')}</option>
        </select>
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

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : data.items.length === 0 ? (
        <div className="card py-16 text-center">
          <Users className="w-12 h-12 mx-auto text-faint mb-4" />
          <p className="text-muted">{t('candidates.emptyTitle')}</p>
        </div>
      ) : (
        <>
          <div className="card overflow-hidden mb-4">
            <table className="w-full">
              <thead>
                <tr className="border-b border-line">
                  <th className="text-left text-xs font-semibold text-muted uppercase tracking-wide px-6 py-3">{t('candidates.colCandidate')}</th>
                  <th className="text-left text-xs font-semibold text-muted uppercase tracking-wide px-6 py-3">{t('candidates.colStatus')}</th>
                  <th
                    className="text-left text-xs font-semibold text-muted uppercase tracking-wide px-6 py-3 cursor-pointer select-none hover:text-content"
                    onClick={() => toggleSort('score')}
                  >{t('candidates.colScore')} <SortIcon col="score" /></th>
                  <th className="text-left text-xs font-semibold text-muted uppercase tracking-wide px-6 py-3" title={t('candidates.preScreenHint')}>{t('candidates.colPreScreen')}</th>
                  <th className="text-left text-xs font-semibold text-muted uppercase tracking-wide px-6 py-3">{t('candidates.colRecommendation')}</th>
                  <th
                    className="text-left text-xs font-semibold text-muted uppercase tracking-wide px-6 py-3 cursor-pointer select-none hover:text-content"
                    onClick={() => toggleSort('created_at')}
                  >{t('candidates.colDate')} <SortIcon col="created_at" /></th>
                  <th className="px-6 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data.items.map(c => (
                  <tr key={c.id} className="hover:bg-surface-muted transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div>
                          <p className="text-sm font-medium text-content">{c.name}</p>
                          <p className="text-xs text-faint">{c.email}</p>
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
