import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'

import ScoreBadge from '../ScoreBadge'
import StatusBadge from '../StatusBadge'
import RecommendationBadge from '../RecommendationBadge'
import Spinner from '../Spinner'
import { LanguageProvider } from '../../i18n'

function withLang(children) {
  return <LanguageProvider>{children}</LanguageProvider>
}

describe('ScoreBadge', () => {
  it('показывает прочерк, если score отсутствует', () => {
    render(<ScoreBadge score={null} />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('зелёный для score >= 75', () => {
    render(<ScoreBadge score={80} />)
    const badge = screen.getByText('80')
    expect(badge).toHaveClass('bg-green-100', 'text-green-800')
  })

  it('жёлтый для score от 50 до 74', () => {
    render(<ScoreBadge score={60} />)
    expect(screen.getByText('60')).toHaveClass('bg-yellow-100')
  })

  it('красный для score < 50', () => {
    render(<ScoreBadge score={30} />)
    expect(screen.getByText('30')).toHaveClass('bg-red-100')
  })

  it('округляет дробный score, но цвет берёт от исходного значения', () => {
    render(<ScoreBadge score={74.6} />)
    // 74.6 отображается как 75, но порог 75 не достигнут — жёлтый
    expect(screen.getByText('75')).toHaveClass('bg-yellow-100')
  })
})

describe('StatusBadge', () => {
  it.each([
    ['applied', 'Заявка'],
    ['interviewing', 'Интервью'],
    ['completed', 'Завершено'],
    ['hired', 'Принят'],
    ['rejected', 'Отказано'],
  ])('статус %s → лейбл «%s» (ru по умолчанию)', (status, label) => {
    render(withLang(<StatusBadge status={status} />))
    expect(screen.getByText(label)).toBeInTheDocument()
  })

  it('неизвестный статус показывается как есть (fallback)', () => {
    render(withLang(<StatusBadge status="custom_stage" />))
    expect(screen.getByText('custom_stage')).toHaveClass('bg-surface-muted')
  })
})

describe('RecommendationBadge', () => {
  it('прочерк без значения', () => {
    render(withLang(<RecommendationBadge value={null} />))
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it.each([
    ['hire', 'Нанять'],
    ['maybe', 'Возможно'],
    ['reject', 'Отказать'],
  ])('рекомендация %s → «%s» (ru по умолчанию)', (value, label) => {
    render(withLang(<RecommendationBadge value={value} />))
    expect(screen.getByText(label)).toBeInTheDocument()
  })

  it('неизвестное значение показывается как есть', () => {
    render(withLang(<RecommendationBadge value="strong_hire" />))
    expect(screen.getByText('strong_hire')).toBeInTheDocument()
  })
})

describe('Spinner', () => {
  it('размер по умолчанию md', () => {
    const { container } = render(<Spinner />)
    expect(container.firstChild).toHaveClass('w-6', 'h-6', 'animate-spin')
  })

  it('размер lg', () => {
    const { container } = render(<Spinner size="lg" />)
    expect(container.firstChild).toHaveClass('w-10', 'h-10')
  })

  it('размер sm', () => {
    const { container } = render(<Spinner size="sm" />)
    expect(container.firstChild).toHaveClass('w-4', 'h-4')
  })
})
