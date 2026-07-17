import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, beforeEach, vi } from 'vitest'

import { ThemeProvider, useTheme } from '../../theme'
import ThemeSwitcher from '../ThemeSwitcher'
import { LanguageProvider } from '../../i18n'

// jsdom не реализует matchMedia — минимальный мок (по умолчанию системная тема светлая).
function mockMatchMedia(matches = false) {
  window.matchMedia = vi.fn().mockImplementation((query) => ({
    matches,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }))
}

function renderSwitcher() {
  return render(
    <ThemeProvider>
      <LanguageProvider>
        <ThemeSwitcher />
      </LanguageProvider>
    </ThemeProvider>
  )
}

describe('ThemeSwitcher / useTheme', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.classList.remove('dark')
    mockMatchMedia(false)
  })

  it('по умолчанию тема system и системная светлая → нет класса dark', () => {
    renderSwitcher()
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('клик по «Тёмная» ставит класс dark и сохраняет выбор', () => {
    renderSwitcher()
    fireEvent.click(screen.getByTitle('Тёмная'))
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('theme')).toBe('dark')
  })

  it('клик по «Светлая» снимает класс dark', () => {
    renderSwitcher()
    fireEvent.click(screen.getByTitle('Тёмная'))
    fireEvent.click(screen.getByTitle('Светлая'))
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(localStorage.getItem('theme')).toBe('light')
  })

  it('system при системной тёмной теме включает класс dark', () => {
    mockMatchMedia(true)
    renderSwitcher()
    // по умолчанию режим system, matchMedia → dark
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('активная кнопка помечена aria-pressed', () => {
    renderSwitcher()
    fireEvent.click(screen.getByTitle('Тёмная'))
    expect(screen.getByTitle('Тёмная')).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByTitle('Светлая')).toHaveAttribute('aria-pressed', 'false')
  })

  it('восстанавливает сохранённую тему из localStorage', () => {
    localStorage.setItem('theme', 'dark')
    function Probe() {
      const { theme } = useTheme()
      return <span data-testid="probe">{theme}</span>
    }
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>
    )
    expect(screen.getByTestId('probe').textContent).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })
})
