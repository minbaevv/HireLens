import { useState, useRef, useEffect } from 'react'
import { useT } from '../i18n'
import { SUPPORTED_LANGS } from '../i18n/translations'

// Короткая метка (для кнопки) + родное название (для списка).
const LANG_META = {
  ru: { label: 'РУ', native: 'Русский' },
  ky: { label: 'КЫ', native: 'Кыргызча' },
  en: { label: 'EN', native: 'English' },
}

export default function LanguageSwitcher() {
  const { lang, setLang } = useT()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    const onKey = (e) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const current = LANG_META[lang] || LANG_META.ru

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Выбор языка"
        className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs font-medium text-content hover:bg-surface-muted transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-3.5 w-3.5">
          <circle cx="12" cy="12" r="10" />
          <path d="M2 12h20" />
          <path d="M12 2a15.3 15.3 0 0 1 0 20 15.3 15.3 0 0 1 0-20z" />
        </svg>
        <span>{current.label}</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={`h-3 w-3 transition-transform ${open ? 'rotate-180' : ''}`}>
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {open && (
        <ul
          role="listbox"
          className="absolute right-0 z-50 mt-1 w-40 overflow-hidden rounded-lg border border-line bg-surface shadow-lg animate-fade-in"
        >
          {SUPPORTED_LANGS.map((code) => {
            const meta = LANG_META[code] || { label: code, native: code }
            const active = code === lang
            return (
              <li key={code} role="option" aria-selected={active}>
                <button
                  type="button"
                  onClick={() => {
                    setLang(code)
                    setOpen(false)
                  }}
                  className={`flex w-full items-center justify-between px-3 py-2 text-sm transition-colors ${
                    active ? 'bg-brand-600 text-white' : 'text-content hover:bg-surface-muted'
                  }`}
                >
                  <span>{meta.native}</span>
                  <span className={active ? 'text-white/80' : 'text-muted'}>{meta.label}</span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
