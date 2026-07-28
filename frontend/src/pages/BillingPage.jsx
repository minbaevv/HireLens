import { useEffect, useRef, useState } from 'react'
import { CreditCard, CheckCircle2, AlertTriangle, Building2, Wallet, MessageCircle, Upload, Clock, XCircle } from 'lucide-react'
import api from '../api/client'
import { useT } from '../i18n'
import { fmtDate } from '../utils/datetime'

// Свой QR: положи картинку ПРЯМО в frontend/public/ с именем
// payment-qr и любым расширением: payment-qr.jpg / .png / .jpeg / .webp.
// Например: frontend/public/payment-qr.jpg
// Или укажи ссылку в переменной VITE_PAYMENT_QR_URL.
const QR_CANDIDATES = import.meta.env.VITE_PAYMENT_QR_URL
  ? [import.meta.env.VITE_PAYMENT_QR_URL]
  : ['/payment-qr.jpg', '/payment-qr.jpeg', '/payment-qr.png', '/payment-qr.webp']

const STATUS_META = {
  pending: { key: 'billing.rPending', icon: Clock, cls: 'text-amber-600 dark:text-amber-400' },
  approved: { key: 'billing.rApproved', icon: CheckCircle2, cls: 'text-green-600 dark:text-green-400' },
  rejected: { key: 'billing.rRejected', icon: XCircle, cls: 'text-red-600 dark:text-red-400' },
}

export default function BillingPage() {
  const { t } = useT()
  const [data, setData] = useState(null)
  const [receipts, setReceipts] = useState([])
  const [plan, setPlan] = useState('starter')
  const [uploading, setUploading] = useState(false)
  const [msg, setMsg] = useState(null)
  const [qrIdx, setQrIdx] = useState(0)
  const fileRef = useRef(null)

  const loadReceipts = () => api.get('/billing/receipts').then(r => setReceipts(r.data)).catch(() => {})
  useEffect(() => {
    api.get('/billing/me').then(r => setData(r.data)).catch(() => {})
    loadReceipts()
  }, [])

  const pi = data?.payment_info || {}
  const expired = data && !data.active
  const currency = pi.currency || 'сом'

  const submitReceipt = async (e) => {
    e.preventDefault()
    const f = fileRef.current?.files?.[0]
    if (!f) { setMsg({ ok: false, text: t('billing.receiptPickFile') }); return }
    const fd = new FormData()
    fd.append('plan', plan)
    fd.append('file', f)
    setUploading(true)
    setMsg(null)
    try {
      await api.post('/billing/receipt', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      setMsg({ ok: true, text: t('billing.receiptSent') })
      if (fileRef.current) fileRef.current.value = ''
      await loadReceipts()
    } catch {
      setMsg({ ok: false, text: t('billing.receiptError') })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="p-6 md:p-8 max-w-3xl mx-auto">
      <div className="flex items-center gap-3 mb-1">
        <div className="inline-flex p-2 rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
          <CreditCard className="w-6 h-6" />
        </div>
        <h1 className="page-title">{t('billing.title')}</h1>
      </div>
      {data?.is_free && <p className="text-muted mb-6">{t('billing.freeDesc')}</p>}

      {expired && (
        <div className="card p-4 mb-6 border-red-300 bg-red-50 dark:bg-red-500/10 flex items-center gap-2 text-red-700 dark:text-red-300">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm">{t('billing.expiredWarning')}</span>
        </div>
      )}

      <div className="card p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <span className="text-sm text-muted">{t('billing.currentPlan')}</span>
          <span className="text-lg font-bold text-content uppercase">{data?.plan || '—'}</span>
        </div>
        <div className="flex items-center justify-between mb-4">
          <span className="text-sm text-muted">{t('billing.status')}</span>
          <span className={`inline-flex items-center gap-1.5 text-sm font-semibold ${data?.active ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
            {data?.active ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
            {data?.active ? t('billing.active') : t('billing.expired')}
          </span>
        </div>
        {data?.plan_expires_at && (
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted">{t('billing.expiresOn')}</span>
            <span className="text-sm text-content">{fmtDate(data.plan_expires_at)}</span>
          </div>
        )}
        {data?.days_left != null && (
          <div className="text-right text-xs text-faint mt-1">{t('billing.daysLeft', { count: data.days_left })}</div>
        )}
      </div>

      <div className="card p-6 mb-6">
        <h2 className="section-title mb-4">{t('billing.howToPay')}</h2>
        {pi.note && <p className="text-sm text-muted mb-4">{pi.note}</p>}
        <dl className="space-y-3 text-sm">
          <div className="flex items-center gap-3"><Building2 className="w-4 h-4 text-brand-600 dark:text-brand-300 flex-shrink-0" /><span className="text-muted w-36">{t('billing.bank')}</span><span className="text-content font-medium">{pi.bank}</span></div>
          <div className="flex items-center gap-3"><Wallet className="w-4 h-4 text-brand-600 dark:text-brand-300 flex-shrink-0" /><span className="text-muted w-36">{t('billing.account')}</span><span className="text-content font-medium tracking-wide">{pi.account}</span></div>
          <div className="flex items-center gap-3"><Building2 className="w-4 h-4 text-brand-600 dark:text-brand-300 flex-shrink-0" /><span className="text-muted w-36">{t('billing.recipient')}</span><span className="text-content font-medium">{pi.recipient}</span></div>
          <div className="flex items-center gap-3"><MessageCircle className="w-4 h-4 text-brand-600 dark:text-brand-300 flex-shrink-0" /><span className="text-muted w-36">{t('billing.contact')}</span><span className="text-content font-medium">{pi.contact}</span></div>
        </dl>
        {qrIdx < QR_CANDIDATES.length && (
          <div className="mt-6 flex flex-col items-center">
            <img src={QR_CANDIDATES[qrIdx]} onError={() => setQrIdx(i => i + 1)} alt="QR" width={180} height={180} className="rounded-xl border border-line bg-white p-2 object-contain" />
            <span className="text-xs text-faint mt-2">{t('billing.scanQr')}</span>
          </div>
        )}
      </div>

      <div className="card p-6">
        <div className="flex items-center gap-2 mb-4">
          <Upload className="w-5 h-5 text-brand-600 dark:text-brand-300" />
          <h2 className="section-title">{t('billing.uploadReceipt')}</h2>
        </div>
        <form onSubmit={submitReceipt} className="flex flex-col sm:flex-row sm:items-end gap-3">
          <label className="flex-1">
            <span className="block text-xs text-muted mb-1">{t('billing.selectPlan')}</span>
            <select value={plan} onChange={e => setPlan(e.target.value)} className="input w-full">
              <option value="starter">Starter — {pi.prices?.starter ?? 4900} {currency}</option>
              <option value="pro">Pro — {pi.prices?.pro ?? 12900} {currency}</option>
            </select>
          </label>
          <label className="flex-1">
            <span className="block text-xs text-muted mb-1">{t('billing.receiptFile')}</span>
            <input ref={fileRef} type="file" accept="image/*,.pdf" className="input w-full py-1.5" />
          </label>
          <button type="submit" disabled={uploading} className="btn-primary px-4 py-2 whitespace-nowrap">
            {uploading ? '…' : t('billing.sendReceipt')}
          </button>
        </form>
        {msg && (
          <p className={`text-sm mt-3 ${msg.ok ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>{msg.text}</p>
        )}

        <div className="mt-6">
          <h3 className="text-sm font-semibold text-content mb-3">{t('billing.myReceipts')}</h3>
          {receipts.length === 0 ? (
            <p className="text-sm text-faint">{t('billing.noReceipts')}</p>
          ) : (
            <ul className="space-y-2">
              {receipts.map(r => {
                const meta = STATUS_META[r.status] || STATUS_META.pending
                const Icon = meta.icon
                return (
                  <li key={r.id} className="flex items-center justify-between text-sm border-b border-line pb-2 last:border-0">
                    <span className="text-muted">{fmtDate(r.created_at)} · <span className="uppercase">{r.plan_requested}</span></span>
                    <span className={`inline-flex items-center gap-1.5 font-medium ${meta.cls}`}><Icon className="w-4 h-4" />{t(meta.key)}</span>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
