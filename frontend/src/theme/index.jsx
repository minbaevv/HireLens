import { createContext, useContext, useEffect, useState } from 'react'

const ThemeContext = createContext(null)

export const THEME_OPTIONS = ['light', 'dark', 'system']
const DEFAULT_THEME = 'system'
const STORAGE_KEY = 'theme'
const DARK_QUERY = '(prefers-color-scheme: dark)'

/** Возвращает true, если при выбранном режиме итоговая тема — тёмная. */
function resolveIsDark(theme) {
  if (theme === 'dark') return true
  if (theme === 'light') return false
  // system
  return typeof window !== 'undefined' && window.matchMedia(DARK_QUERY).matches
}

/** Применяет/снимает класс `dark` на <html> — синхронно с CSS-токенами. */
function applyTheme(theme) {
  const isDark = resolveIsDark(theme)
  document.documentElement.classList.toggle('dark', isDark)
  return isDark
}

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    return THEME_OPTIONS.includes(saved) ? saved : DEFAULT_THEME
  })

  const setTheme = (next) => {
    if (!THEME_OPTIONS.includes(next)) return
    setThemeState(next)
    localStorage.setItem(STORAGE_KEY, next)
  }

  // Применяем тему при смене выбора.
  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  // В режиме system реагируем на смену системной темы вживую.
  useEffect(() => {
    if (theme !== 'system') return
    const mq = window.matchMedia(DARK_QUERY)
    const handler = () => applyTheme('system')
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [theme])

  const isDark = resolveIsDark(theme)

  return (
    <ThemeContext.Provider value={{ theme, setTheme, isDark }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme должен использоваться внутри ThemeProvider')
  return ctx
}
