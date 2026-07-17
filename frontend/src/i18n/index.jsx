import { createContext, useContext, useEffect, useState } from 'react'

import { DEFAULT_LANG, SUPPORTED_LANGS, translations } from './translations'

const LanguageContext = createContext(null)

// Индекс формы множественного числа по правилам языка.
// ru: 3 формы [1, 2-4, 5+] · en: 2 формы [1, прочее] · ky: 1 форма (после числа без изменений).
function pluralIndex(lang, n) {
  n = Math.abs(Number(n) || 0)
  if (lang === 'ru') {
    const m10 = n % 10, m100 = n % 100
    if (m10 === 1 && m100 !== 11) return 0
    if (m10 >= 2 && m10 <= 4 && !(m100 >= 12 && m100 <= 14)) return 1
    return 2
  }
  if (lang === 'en') return n === 1 ? 0 : 1
  return 0 // ky и др. — единая форма
}

// Выбирает форму из шаблона вида "1 вакансия|2 вакансии|5 вакансий" по count.
function selectPlural(lang, n, forms) {
  const idx = pluralIndex(lang, n)
  return forms[Math.min(idx, forms.length - 1)] ?? forms[0]
}

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(() => {
    const saved = localStorage.getItem('lang')
    return SUPPORTED_LANGS.includes(saved) ? saved : DEFAULT_LANG
  })

  const setLang = (next) => {
    if (!SUPPORTED_LANGS.includes(next)) return
    setLangState(next)
    localStorage.setItem('lang', next)
  }

  useEffect(() => {
    document.documentElement.lang = lang
  }, [lang])

  // t('apply.about') → перевод; fallback: русский → сам ключ
  // t('dashboard.activeJobs', { count: 5 }) → подставляет {count} в шаблоне перевода
  // Плюрализация: если шаблон содержит формы через "|" и передан count,
  //   выбирается форма по правилу языка: "{count} вакансия|{count} вакансии|{count} вакансий"
  const t = (key, params) => {
    let template = translations[lang]?.[key] ?? translations[DEFAULT_LANG][key] ?? key
    if (!params) return template
    if (template.includes('|') && params.count != null) {
      template = selectPlural(lang, params.count, template.split('|'))
    }
    return Object.entries(params).reduce(
      (acc, [k, v]) => acc.replaceAll(`{${k}}`, v),
      template
    )
  }

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useT() {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error('useT должен использоваться внутри LanguageProvider')
  return ctx
}
