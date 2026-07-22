import { useEffect, useState } from 'react'
import { Palette, Save, Check } from 'lucide-react'
import api from '../api/client'
import { useT } from '../i18n'

const HEX_RE = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/

export default function BrandingPage() {
  const { t } = useT()
  const [enabled, setEnabled] = useState(false)
  const [name, setName] = useState('')
  const [logoUrl, setLogoUrl] = useState('')
  const [color, setColor] = useState('#2563EB')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)

  useEffect(() => {
    api.get('/branding')
      .then(r => {
        const d = r.data || {}
        setEnabled(!!d.enabled)
        setName(d.name || '')
        setLogoUrl(d.logo_url || '')
        setColor(d.color || '#2563EB')
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const save = async () => {
    setSaving(true)
    setMsg(null)
    try {
      await api.put('/branding', {
        enabled,
        name: name.trim() || null,
        logo_url: logoUrl.trim() || null,
        color: color || null,
      })
      setMsg({ ok: true, text: t('branding.saved') })
    } catch (e) {
      setMsg({ ok: false, text: e.response?.data?.detail || t('branding.saveError') })
    } finally {
      setSaving(false)
    }
  }

  const safeColor = HEX_RE.test(color) ? color : '#2563EB'
  const initial = (name || 'H').trim().charAt(0).toUpperCase()

  return (
    <div className="p-6 md:p-8 max-w-3xl mx-auto">
      <div className="flex items-center gap-3 mb-1">
        <div className="inline-flex p-2 rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
          <Palette className="w-6 h-6" />
        </div>
        <h1 className="text-2xl font-bold text-content">{t('branding.title')}</h1>
      </div>
      <p className="text-muted mb-6">{t('branding.subtitle')}</p>

      {loading ? (
        <div className="card p-6 text-muted">…</div>
      ) : (
        <>
          <div className="card p-6 mb-6 space-y-5">
            <label className="flex items-center justify-between gap-4 cursor-pointer">
              <span>
                <span className="block text-sm font-semibold text-content">{t('branding.enable')}</span>
                <span className="block text-xs text-muted mt-0.5">{t('branding.enableHint')}</span>
              </span>
              <input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} className="w-5 h-5 accent-brand-600" />
            </label>

            <div>
              <label className="block text-xs text-muted mb-1">{t('branding.name')}</label>
              <input value={name} onChange={e => setName(e.target.value)} maxLength={120} placeholder="Acme Inc." className="input w-full" />
            </div>

            <div>
              <label className="block text-xs text-muted mb-1">{t('branding.logoUrl')}</label>
              <input value={logoUrl} onChange={e => setLogoUrl(e.target.value)} placeholder="https://…/logo.png" className="input w-full" />
              <p className="text-xs text-faint mt-1">{t('branding.logoHint')}</p>
            </div>

            <div>
              <label className="block text-xs text-muted mb-1">{t('branding.color')}</label>
              <div className="flex items-center gap-3">
                <input type="color" value={safeColor} onChange={e => setColor(e.target.value)} className="w-12 h-10 rounded-lg border border-line bg-transparent cursor-pointer" />
                <input value={color} onChange={e => setColor(e.target.value)} maxLength={9} placeholder="#2563EB" className="input w-40" />
              </div>
            </div>
          </div>

          <div className="card p-6 mb-6">
            <h2 className="text-sm font-semibold text-content mb-4">{t('branding.preview')}</h2>
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl flex items-center justify-center overflow-hidden text-white font-bold" style={{ backgroundColor: safeColor }}>
                {logoUrl ? <img src={logoUrl} alt="" className="w-full h-full object-contain" /> : initial}
              </div>
              <div>
                <p className="text-sm font-bold text-content">{enabled && name ? name : 'HireLens'}</p>
                <p className="text-xs text-faint">{t('branding.previewCaption')}</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button onClick={save} disabled={saving} className="btn-primary px-5 py-2 inline-flex items-center gap-2">
              <Save className="w-4 h-4" />{saving ? '…' : t('branding.save')}
            </button>
            {msg && (
              <span className={`text-sm inline-flex items-center gap-1 ${msg.ok ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                {msg.ok && <Check className="w-4 h-4" />}{msg.text}
              </span>
            )}
          </div>
        </>
      )}
    </div>
  )
}
