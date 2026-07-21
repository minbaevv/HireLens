import { useEffect, useState } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { LayoutDashboard, Briefcase, Users, LogOut, LayoutGrid, BarChart2, Sparkles, UserCog, CreditCard, ShieldCheck, Plug, Scale, Code2, Search } from 'lucide-react'
import api from '../api/client'
import { useT } from '../i18n'
import Logo from './Logo'
import LanguageSwitcher from './LanguageSwitcher'
import ThemeSwitcher from './ThemeSwitcher'
import CommandPalette from './CommandPalette'

export default function Layout() {
  const { company, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const { t } = useT()
  const [isSuperadmin, setIsSuperadmin] = useState(false)

  useEffect(() => {
    api.get('/billing/me').then(r => setIsSuperadmin(!!r.data?.is_superadmin)).catch(() => {})
  }, [])

  const navItems = [
    { to: '/',           icon: LayoutDashboard, label: t('nav.dashboard'), end: true },
    { to: '/jobs',       icon: Briefcase,       label: t('nav.jobs') },
    { to: '/candidates', icon: Users,           label: t('nav.candidates') },
    { to: '/kanban',     icon: LayoutGrid,      label: t('nav.kanban') },
    { to: '/analytics',  icon: BarChart2,       label: t('nav.analytics') },
    { to: '/copilot',    icon: Sparkles,        label: t('nav.copilot') },
    { to: '/team',       icon: UserCog,         label: t('nav.team') },
    { to: '/integrations', icon: Plug,          label: t('nav.integrations') },
    { to: '/governance', icon: Scale,          label: t('nav.governance') },
    { to: '/coding',     icon: Code2,          label: t('nav.coding') },
    { to: '/billing',    icon: CreditCard,      label: t('nav.billing') },
  ]

  if (isSuperadmin) {
    navItems.push({ to: '/admin', icon: ShieldCheck, label: t('nav.admin') })
  }

  return (
    <div className="flex h-screen bg-canvas">
      <CommandPalette />
      <aside className="w-64 bg-surface border-r border-line flex flex-col">
        <div className="px-6 py-5 border-b border-line">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-[#0b1e3f] rounded-xl flex items-center justify-center">
              <Logo className="w-6 h-6" title="HireLens" />
            </div>
            <div>
              <p className="text-sm font-bold text-content">HireLens</p>
              <p className="text-xs text-faint">AI-скрининг кандидатов</p>
            </div>
          </div>
        </div>

        <nav className="px-3 py-4 space-y-1">
          <button
            onClick={() => window.dispatchEvent(new Event('open-command-palette'))}
            className="flex items-center gap-2 w-full px-3 py-2 mb-2 rounded-lg border border-line text-sm text-faint hover:bg-surface-muted hover:text-muted transition-colors"
          >
            <Search className="w-4 h-4" />
            <span className="flex-1 text-left">{t('palette.open')}</span>
            <kbd className="text-[10px] border border-line rounded px-1.5 py-0.5">Ctrl K</kbd>
          </button>
          {navItems.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to} to={to} end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300' : 'text-muted hover:bg-surface-muted hover:text-content'
                }`
              }
            >
              <Icon className="w-4 h-4" />{label}
            </NavLink>
          ))}

          {/* Переключатели — сразу под меню, чтобы не оставлять «провал пустоты» */}
          <div className="pt-3 mt-3 border-t border-line flex items-center justify-between gap-2 px-1">
            <LanguageSwitcher />
            <ThemeSwitcher />
          </div>
        </nav>

        {/* Низ: пользователь + выход, прижаты к нижней кромке */}
        <div className="mt-auto px-3 py-4 border-t border-line space-y-2">
          {company && (
            <div className="px-3 py-1">
              <p className="text-xs font-semibold text-content truncate">{company.name}</p>
              <p className="text-xs text-faint truncate">{company.email}</p>
            </div>
          )}
          <button
            onClick={() => { logout(); navigate('/login') }}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-muted hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/15 dark:hover:text-red-400 transition-colors"
          >
            <LogOut className="w-4 h-4" />{t('nav.logout')}
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <div key={location.pathname} className="animate-fade-in">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
