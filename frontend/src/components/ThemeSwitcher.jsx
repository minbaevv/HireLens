import { Sun, Moon, Monitor } from 'lucide-react'

import { useTheme, THEME_OPTIONS } from '../theme'
import { useT } from '../i18n'

const ICONS = { light: Sun, dark: Moon, system: Monitor }

export default function ThemeSwitcher() {
  const { theme, setTheme } = useTheme()
  const { t } = useT()

  return (
    <div
      role="group"
      aria-label={t('theme.label')}
      className="inline-flex rounded-lg border border-line overflow-hidden text-xs"
    >
      {THEME_OPTIONS.map((option) => {
        const Icon = ICONS[option]
        const active = theme === option
        return (
          <button
            key={option}
            type="button"
            onClick={() => setTheme(option)}
            aria-pressed={active}
            title={t(`theme.${option}`)}
            className={`px-2.5 py-1.5 transition-colors ${
              active
                ? 'bg-brand-600 text-white'
                : 'bg-surface text-muted hover:bg-surface-muted'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
          </button>
        )
      })}
    </div>
  )
}
