import { useEffect, useState } from 'react'
import { Shield, Download, Clock, Trash2, AlertTriangle } from 'lucide-react'
import api from '../api/client'
import { useT } from '../i18n'

export default function PrivacyPage() {
  const { t } = useT()
  const [retention, setRetention] = useState('')
  const [savingRet, setSavingRet] = useState(false)
  const [retMsg, setRetMsg] = useState(null)
  const [exporting, setExporting] = useState(false)
  const [confirmEmail, setConfirmEmail] = useState('')
  const [erasing, setErasing] = useState(false)
  const [eraseMsg, setEraseMsg] = useState(null)

  useEffect(() => {
    api.get('/privacy/retention').then(r => setRetention(r.data?.days ?? '')).catch(() => {})
  }, [])

  const exportData = async () => {
    setExporting(true)
    try {
      const { data } = await api.get('/privacy/export')
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `hirelens-export-${new Date().toISOString().slice(0, 10)}.json`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (e) {
      /* ошибка экспорта — тихо игнорируем */
    } finally {
      setExporting(false)
    }
  }

  const saveRetention = async () => {
    setSavingRet(true)
    setRetMsg(null)
    try {
      const days = retention === '' ? null : Number(retention)
      await api.put('/privacy/retention', { days })
      setRetMsg({ ok: true, text: t('privacy.retentionSaved') })
    } catch (e) {
      setRetMsg({ ok: false, text: e.response?.data?.detail || t('privacy.retentionError') })
    } finally {
      setSavingRet(false)
    }
  }

  const erase = async () => {
    if (!window.confirm(t('privacy.eraseConfirm'))) return
    setErasing(true)
    setEraseMsg(null)
    try {
      const { data } = await api.post('/privacy/erase-candidates', { confirm_email: confirmEmail })
      setEraseMsg({ ok: true, text: t('privacy.eraseDone', { count: data?.deleted ?? 0 }) })
      setConfirmEmail('')
    } catch (e) {
      setEraseMsg({ ok: false, text: e.response?.data?.detail || t('privacy.eraseError') })
    } finally {
      setErasing(false)
    }
  }

  return (
    <div className="p-6 md:p-8 max-w-3xl mx-auto">
      <div className="flex items-center gap-3 mb-1">
        <div className="inline-flex p-2 rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
          <Shield className="w-6 h-6" />
        </div>
        <h1 className="text-2xl font-bold text-content">{t('privacy.title')}</h1>
      </div>
      <p className="text-muted mb-6">{t('privacy.subtitle')}</p>

      <div className="card p-6 mb-6">
        <div className="flex items-center gap-2 mb-2"><Download className="w-5 h-5 text-brand-600 dark:text-brand-300" /><h2 className="font-semibold text-content">{t('privacy.exportTitle')}</h2></div>
        <p className="text-sm text-muted mb-4">{t('privacy.exportDesc')}</p>
        <button onClick={exportData} disabled={exporting} className="btn-primary px-4 py-2 inline-flex items-center gap-2"><Download className="w-4 h-4" />{exporting ? '…' : t('privacy.exportBtn')}</button>
      </div>

      <div className="card p-6 mb-6">
        <div className="flex items-center gap-2 mb-2"><Clock className="w-5 h-5 text-brand-600 dark:text-brand-300" /><h2 className="font-semibold text-content">{t('privacy.retentionTitle')}</h2></div>
        <p className="text-sm text-muted mb-4">{t('privacy.retentionDesc')}</p>
        <div className="flex items-center gap-3">
          <input type="number" min="1" max="3650" value={retention} onChange={e => setRetention(e.target.value)} placeholder={t('privacy.retentionForever')} className="input w-40" />
          <span className="text-sm text-muted">{t('privacy.days')}</span>
          <button onClick={saveRetention} disabled={savingRet} className="btn-primary px-4 py-2">{savingRet ? '…' : t('privacy.save')}</button>
        </div>
        {retMsg && <p className={`text-sm mt-3 ${retMsg.ok ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>{retMsg.text}</p>}
      </div>

      <div className="card p-6 border-red-300 dark:border-red-500/40">
        <div className="flex items-center gap-2 mb-2"><AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" /><h2 className="font-semibold text-red-700 dark:text-red-300">{t('privacy.dangerTitle')}</h2></div>
        <p className="text-sm text-muted mb-4">{t('privacy.eraseDesc')}</p>
        <label className="block text-xs text-muted mb-1">{t('privacy.confirmEmail')}</label>
        <div className="flex items-center gap-3">
          <input type="email" value={confirmEmail} onChange={e => setConfirmEmail(e.target.value)} placeholder="you@company.com" className="input flex-1" />
          <button onClick={erase} disabled={erasing || !confirmEmail} className="px-4 py-2 rounded-lg bg-red-600 text-white font-medium hover:bg-red-700 disabled:opacity-50 inline-flex items-center gap-2 whitespace-nowrap"><Trash2 className="w-4 h-4" />{erasing ? '…' : t('privacy.eraseBtn')}</button>
        </div>
        {eraseMsg && <p className={`text-sm mt-3 ${eraseMsg.ok ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>{eraseMsg.text}</p>}
      </div>
    </div>
  )
}
