import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

import InstallPrompt from '../InstallPrompt'
import { LanguageProvider } from '../../i18n'

function fireBeforeInstallPrompt(promptImpl) {
  const event = new Event('beforeinstallprompt', { cancelable: true })
  event.prompt = promptImpl || vi.fn()
  event.userChoice = Promise.resolve({ outcome: 'accepted' })
  window.dispatchEvent(event)
  return event
}

describe('InstallPrompt', () => {
  it('ничего не рендерит, пока не пришло beforeinstallprompt', () => {
    const { container } = render(
      <LanguageProvider>
        <InstallPrompt />
      </LanguageProvider>
    )
    expect(container.firstChild).toBeNull()
  })

  it('показывает кнопку после beforeinstallprompt и вызывает prompt() по клику', async () => {
    const promptSpy = vi.fn()
    render(
      <LanguageProvider>
        <InstallPrompt />
      </LanguageProvider>
    )
    fireBeforeInstallPrompt(promptSpy)

    const button = await screen.findByText('Установить')
    fireEvent.click(button)
    expect(promptSpy).toHaveBeenCalled()
  })

  it('скрывает кнопку после appinstalled', async () => {
    render(
      <LanguageProvider>
        <InstallPrompt />
      </LanguageProvider>
    )
    fireBeforeInstallPrompt()
    await screen.findByText('Установить')

    window.dispatchEvent(new Event('appinstalled'))
    await waitFor(() => expect(screen.queryByText('Установить')).toBeNull())
  })
})
