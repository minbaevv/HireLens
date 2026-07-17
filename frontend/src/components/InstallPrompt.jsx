import { useEffect, useState } from 'react'
import { Download } from 'lucide-react'
import { useT } from '../i18n'

/**
 * Кнопка установки PWA (B3). Появляется только когда браузер
 * сам решил, что приложение можно предложить установить (событие
 * beforeinstallprompt — Android/desktop Chrome и др.). iOS Safari это событие
 * не поддерживает — это ограничение платформы, кнопка там просто не покажется.
 */
export default function InstallPrompt() {
  const { t } = useT()
  const [deferredPrompt, setDeferredPrompt] = useState(null)
  const [installed, setInstalled] = useState(false)

  useEffect(() => {
    function handleBeforeInstall(e) {
      e.preventDefault()
      setDeferredPrompt(e)
    }
    function handleInstalled() {
      setInstalled(true)
      setDeferredPrompt(null)
    }
    window.addEventListener('beforeinstallprompt', handleBeforeInstall)
    window.addEventListener('appinstalled', handleInstalled)
    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstall)
      window.removeEventListener('appinstalled', handleInstalled)
    }
  }, [])

  if (!deferredPrompt || installed) return null

  async function handleInstall() {
    deferredPrompt.prompt()
    await deferredPrompt.userChoice
    setDeferredPrompt(null)
  }

  return (
    <button
      type="button"
      onClick={handleInstall}
      title={t('pwa.installTitle')}
      className="flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:text-brand-700 px-2.5 py-1.5 rounded-lg hover:bg-brand-50 transition-colors"
    >
      <Download className="w-3.5 h-3.5" />
      {t('pwa.install')}
    </button>
  )
}
