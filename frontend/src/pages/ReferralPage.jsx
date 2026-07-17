import { useEffect, useState } from 'react'
import { Gift, Copy, Check, Users, CalendarClock } from 'lucide-react'
import api from '../api/client'
import { useT } from '../i18n'

export default function ReferralPage() {
  const { t } = useT()
  const [info, setInfo] = useState(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    api.get('/referral/me').then(r => setInfo(r.data)).catch(() => {})
  }, [])

  const copy = async () => {
    if (!info?.share_url) return
    try {
      await navigator.clipboard.writeText(info.share_url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { /* clipboard unavailable */ }
  }

  return (
    <div className="p-6 md:p-8 max-w-3xl mx-auto">
      <div className="flex items-center gap-3 mb-1">
        <div className="inline-flex p-2 rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
          <Gift className="w-6 h-6" />
        </div>
        <h1 className="text-2xl font-bold text-content">{t('referral.title')}</h1>
      </div>
      <p className="text-muted mb-6">{t('referral.subtitle')}</p>

      <div className="card p-6 mb-6">
        <label className="block text-sm font-medium text-content mb-2">{t('referral.yourLink')}</label>
        <div className="flex gap-2">
          <input readOnly value={info?.share_url || ''} className="input flex-1" />
          <button onClick={copy} className="btn-primary px-4 whitespace-nowrap inline-flex items-center gap-1.5">
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            {copied ? t('referral.copied') : t('referral.copy')}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        <div className="card p-5 flex items-center gap-3">
          <Users className="w-8 h-8 text-brand-600 dark:text-brand-300" />
          <div className="text-sm text-muted">{t('referral.invited', { count: info?.referred_count ?? 0 })}</div>
        </div>
        <div className="card p-5 flex items-center gap-3">
          <CalendarClock className="w-8 h-8 text-brand-600 dark:text-brand-300" />
          <div className="text-sm text-muted">{t('referral.reward', { count: info?.reward_months ?? 0 })}</div>
        </div>
      </div>

      <div className="card p-6">
        <h2 className="font-semibold text-content mb-3">{t('referral.howTitle')}</h2>
        <ol className="space-y-2 text-sm text-muted list-decimal list-inside">
          <li>{t('referral.how1')}</li>
          <li>{t('referral.how2')}</li>
          <li>{t('referral.how3')}</li>
        </ol>
      </div>
    </div>
  )
}
