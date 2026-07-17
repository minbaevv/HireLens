import { useT } from '../i18n'

const LABELS = { ru: 'РУ', ky: 'КЫ', en: 'EN' }

export default function LanguageSwitcher() {
  const { lang, setLang } = useT()
  return (
    <div className="inline-flex rounded-lg border border-line overflow-hidden text-xs">
      {Object.entries(LABELS).map(([code, label]) => (
        <button
          key={code}
          type="button"
          onClick={() => setLang(code)}
          className={`px-2.5 py-1 font-medium transition-colors ${
            lang === code ? 'bg-brand-600 text-white' : 'bg-surface text-muted hover:bg-surface-muted'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
