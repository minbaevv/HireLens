import { render, screen, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import LanguageSwitcher from '../../components/LanguageSwitcher'
import { LanguageProvider, useT } from '../index'

function Demo() {
  const { t } = useT()
  return (
    <div>
      <span>{t('apply.about')}</span>
      <span>{t('unknown.key')}</span>
    </div>
  )
}

function NavAuthDemo() {
  const { t } = useT()
  return (
    <div>
      <span>{t('nav.dashboard')}</span>
      <span>{t('login.submit')}</span>
      <span>{t('register.submit')}</span>
    </div>
  )
}

describe('i18n', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('по умолчанию русский', () => {
    render(
      <LanguageProvider>
        <Demo />
      </LanguageProvider>
    )
    expect(screen.getByText('О вакансии')).toBeInTheDocument()
  })

  it('неизвестный ключ возвращается как есть', () => {
    render(
      <LanguageProvider>
        <Demo />
      </LanguageProvider>
    )
    expect(screen.getByText('unknown.key')).toBeInTheDocument()
  })

  it('переключение на кыргызский', () => {
    render(
      <LanguageProvider>
        <LanguageSwitcher />
        <Demo />
      </LanguageProvider>
    )
    fireEvent.click(screen.getByText('КЫ'))
    expect(screen.getByText('Вакансия жөнүндө')).toBeInTheDocument()
    expect(localStorage.getItem('lang')).toBe('ky')
  })

  it('переключение на английский', () => {
    render(
      <LanguageProvider>
        <LanguageSwitcher />
        <Demo />
      </LanguageProvider>
    )
    fireEvent.click(screen.getByText('EN'))
    expect(screen.getByText('About the job')).toBeInTheDocument()
  })

  it('сохранённый язык восстанавливается из localStorage', () => {
    localStorage.setItem('lang', 'en')
    render(
      <LanguageProvider>
        <Demo />
      </LanguageProvider>
    )
    expect(screen.getByText('About the job')).toBeInTheDocument()
  })

  it('переводы Login/Register/Nav доступны на русском', () => {
    render(
      <LanguageProvider>
        <NavAuthDemo />
      </LanguageProvider>
    )
    expect(screen.getByText('Дашборд')).toBeInTheDocument()
    expect(screen.getByText('Войти')).toBeInTheDocument()
    expect(screen.getByText('Зарегистрироваться')).toBeInTheDocument()
  })

  it('переводы Login/Register/Nav доступны на кыргызском', () => {
    localStorage.setItem('lang', 'ky')
    render(
      <LanguageProvider>
        <NavAuthDemo />
      </LanguageProvider>
    )
    expect(screen.getByText('Башкы бет')).toBeInTheDocument()
    expect(screen.getByText('Кирүү')).toBeInTheDocument()
    expect(screen.getByText('Катталуу')).toBeInTheDocument()
  })

  it('переводы Login/Register/Nav доступны на английском', () => {
    localStorage.setItem('lang', 'en')
    render(
      <LanguageProvider>
        <NavAuthDemo />
      </LanguageProvider>
    )
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Sign in')).toBeInTheDocument()
    expect(screen.getByText('Sign up')).toBeInTheDocument()
  })
})
