import { useEffect, useState } from 'react'
import { ShieldCheck, FileText, Check, X } from 'lucide-react'
import api from '../api/client'
import { useT } from '../i18n'
import { fmtDate } from '../utils/datetime'

const PLANS = ['free', 'starter', 'pro']

const RSTATUS_CLS = {
  pending: 'text-amber-600 dark:text-amber-400',
  approved: 'text-green-600 dark:text-green-400',
  rejected: 'text-red-600 dark:text-red-400',
}

export default function AdminPage() {
  const { t } = useT()
  const [rows, setRows] = useState([])
  const [receipts, setReceipts] = useState([])
  const [savingId, setSavingId] = useState(null)
  const [drafts, setDrafts] = useState({})

  const load = () => api.get('/admin/companies').then(r => setRows(r.data)).catch(() => {})
  const loadReceipts = () => api.get('/admin/receipts').then(r => setReceipts(r.data)).catch(() => {})
  useEffect(() => { load(); loadReceipts() }, [])

  const draft = (id) => drafts[id] || { plan: 'starter', months: 1 }
  const setDraft = (id, patch) => setDrafts(d => ({ ...d, [id]: { ...draft(id), ...patch } }))

  const setPlan = async (id) => {
    const d = draft(id)
    setSavingId(id)
    try {
      await api.post(`/admin/companies/${id}/plan`, { plan: d.plan, months: d.plan === 'free' ? null : Number(d.months) })
      await load()
    } finally { setSavingId(null) }
  }

  const grantBonus = async (id) => {
    const d = draft(id)
    setSavingId(id)
    try {
      await api.post(`/admin/companies/${id}/grant-bonus`, { months: Number(d.months) || 1 })
      await load()
    } finally { setSavingId(null) }
  }

  const viewReceipt = async (id) => {
    try {
      const res = await api.get(`/admin/receipts/${id}/file`, { responseType: 'blob' })
      const url = URL.createObjectURL(res.data)
      window.open(url, '_blank')
    } catch { /* ignore */ }
  }

  const review = async (id, status) => {
    try {
      await api.post(`/admin/receipts/${id}/review`, { status })
      await loadReceipts()
    } catch { /* ignore */ }
  }

  return (
    <div className="p-6 md:p-8 max-w-5xl mx-auto">
      <div className="flex items-center gap-3 mb-1">
        <div className="inline-flex p-2 rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
          <ShieldCheck className="w-6 h-6" />
        </div>
        <h1 className="page-title">{t('admin.title')}</h1>
      </div>
      <p className="text-muted mb-6">{t('admin.subtitle')}</p>

      <div className="card overflow-x-auto mb-8">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-muted border-b border-line">
              <th className="px-4 py-3">{t('admin.company')}</th>
              <th className="px-4 py-3">{t('admin.plan')}</th>
              <th className="px-4 py-3">{t('admin.expires')}</th>
              <th className="px-4 py-3">{t('admin.months')}</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => {
              const d = draft(r.id)
              return (
                <tr key={r.id} className="border-b border-line last:border-0">
                  <td className="px-4 py-3">
                    <div className="font-medium text-content">{r.name}</div>
                    <div className="text-xs text-faint">{r.email}</div>
                  </td>
                  <td className="px-4 py-3">
                    <select value={d.plan} onChange={e => setDraft(r.id, { plan: e.target.value })} className="input py-1">
                      {PLANS.map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                    <div className="text-xs text-faint mt-1 uppercase">{r.plan}</div>
                  </td>
                  <td className="px-4 py-3 text-muted">{r.plan_expires_at ? fmtDate(r.plan_expires_at) : t('admin.never')}</td>
                  <td className="px-4 py-3">
                    <input type="number" min="1" max="36" value={d.months} onChange={e => setDraft(r.id, { months: e.target.value })} className="input py-1 w-20" />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <button disabled={savingId === r.id} onClick={() => setPlan(r.id)} className="btn-primary px-3 py-1.5 text-xs mr-2">{t('admin.setPlan')}</button>
                    <button disabled={savingId === r.id} onClick={() => grantBonus(r.id)} className="text-xs px-3 py-1.5 rounded-lg border border-line text-muted hover:text-content hover:border-brand-400">{t('admin.grantBonus')}</button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center gap-2 mb-3">
        <FileText className="w-5 h-5 text-brand-600 dark:text-brand-300" />
        <h2 className="text-lg font-semibold text-content">{t('admin.receipts')}</h2>
      </div>
      <div className="card overflow-x-auto">
        {receipts.length === 0 ? (
          <p className="text-sm text-faint p-4">{t('admin.noReceipts')}</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted border-b border-line">
                <th className="px-4 py-3">{t('admin.company')}</th>
                <th className="px-4 py-3">{t('admin.plan')}</th>
                <th className="px-4 py-3">{t('admin.date')}</th>
                <th className="px-4 py-3">{t('admin.status')}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {receipts.map(r => (
                <tr key={r.id} className="border-b border-line last:border-0">
                  <td className="px-4 py-3">
                    <div className="font-medium text-content">{r.company_name}</div>
                    <div className="text-xs text-faint">{r.company_email}</div>
                  </td>
                  <td className="px-4 py-3 uppercase text-muted">{r.plan_requested}</td>
                  <td className="px-4 py-3 text-muted">{r.created_at ? fmtDate(r.created_at) : '—'}</td>
                  <td className={`px-4 py-3 font-medium ${RSTATUS_CLS[r.status] || ''}`}>{r.status}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <button onClick={() => viewReceipt(r.id)} className="text-xs px-3 py-1.5 rounded-lg border border-line text-muted hover:text-content hover:border-brand-400 mr-2">{t('admin.viewReceipt')}</button>
                    <button onClick={() => review(r.id, 'approved')} className="inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg bg-green-600 text-white hover:bg-green-700 mr-2"><Check className="w-3.5 h-3.5" />{t('admin.approve')}</button>
                    <button onClick={() => review(r.id, 'rejected')} className="inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg border border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-red-500/10"><X className="w-3.5 h-3.5" />{t('admin.reject')}</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
