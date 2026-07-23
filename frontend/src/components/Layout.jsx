import { useEffect, useState } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { LayoutDashboard, Briefcase, Users, LogOut, LayoutGrid, BarChart2, Sparkles, UserCog, CreditCard, ShieldCheck, Plug, Scale, Code2, ScrollText, Search, Palette, Shield, Menu, X } from 'lucide-react'
import api from '../api/client'
import { useT } from '../i18n'
import Logo from './Logo'
import LanguageSwitcher from './LanguageSwitcher'
import ThemeSwitcher from './ThemeSwitcher'
import CommandPalette from './CommandPalette'
import AnimatedBackground from './AnimatedBackground'

export default function Layout() {
  const { company, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const { t } = useT()
  const [isSuperadmin, setIsSuperadmin] = useState(false)
  const [brand, setBrand] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [logoError, setLogoError] = useState(false)

  useEffect(() => {
    api.get('/billing/me').then(r => setIsSuperadmin(!!r.data?.is_superadmin)).catch(() => {})
    api.get('/branding').then(r => { setBrand(r.data); setLogoError(false) }).catch(() => {})
  }, [])

  // Close mobile drawer on route change
  useEffect(() => { setSidebarOpen(false) }, [location.pathname])

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
    { to: '/audit',      icon: ScrollText,      label: t('nav.audit') },
    { to: '/branding',   icon: Palette,         label: t('nav.branding') },
    { to: '/privacy',    icon: Shield,          label: t('nav.privacy') },
  ]

  if (isSuperadmin) {
    navItems.push({ to: '/admin', icon: ShieldCheck, label: t('nav.admin') })
  }

  const showCustomLogo = !!(brand?.enabled && brand?.logo_url && !logoError)

  return (
    <div className="flex h-screen bg-canvas">
      <AnimatedBackground variant="app" />
      <CommandPalette />

      {/* Mobile top bar with hamburger */}
      <div className="md:hidden fixed top-0 inset-x-0 z-30 h-14 flex items-center gap-3 px-4 bg-surface/90 backdrop-blur-xl border-b border-line">
        <button onClick={() => setSidebarOpen(true)} className="p-2 -ml-2 rounded-lg text-muted hover:bg-surface-muted" aria-label="Menu">
          <Menu className="w-5 h-5" />
        </button>
        <div
          className="w-7 h-7 bg-[#0b1e3f] rounded-lg flex items-center justify-center overflow-hidden"
          style={showCustomLogo && /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(brand?.color || '') ? { backgroundColor: brand.color } : undefined}
        >
          {showCustomLogo
            ? <img src={brand.logo_url} alt="" className="w-full h-full object-contain" onError={() => setLogoError(true)} />
            : <Logo className="w-5 h-5" title="HireLens" />}
        </div>
        <p className="text-sm font-bold text-content">{brand?.enabled && brand?.name ? brand.name : 'HireLens'}</p>
      </div>

      {/* Backdrop for mobile drawer */}
      {sidebarOpen && (
        <div className="md:hidden fixed inset-0 z-40 bg-black/50" onClick={() => setSidebarOpen(false)} />
      )}

      <aside className={`fixed md:relative inset-y-0 left-0 z-50 md:z-10 w-64 bg-surface/85 backdrop-blur-xl border-r border-line flex flex-col transform transition-transform duration-200 md:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="px-6 py-5 border-b border-line">
          <button onClick={() => setSidebarOpen(false)} className="md:hidden absolute top-4 right-3 p-2 rounded-lg text-muted hover:bg-surface-muted" aria-label="Close">
            <X className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 bg-[#0b1e3f] rounded-xl flex items-center justify-center overflow-hidden"
              style={showCustomLogo && /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(brand?.color || '') ? { backgroundColor: brand.color } : undefined}
            >
              {showCustomLogo
                ? <img src={brand.logo_url} alt="" className="w-full h-full object-contain" onError={() => setLogoError(true)} />
                : <Logo className="w-6 h-6" title="HireLens" />}
            </div>
            <div>
              <p className="text-sm font-bold text-content">{brand?.enabled && brand?.name ? brand.name : 'HireLens'}</p>
              <p className="text-xs text-faint">AI-скрининг кандидатов</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
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
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300' : 'text-muted hover:bg-surface-muted hover:text-content'
                }`
              }
            >
              <Icon className="w-4 h-4" />{label}
            </NavLink>
          ))}

        </nav>

        {/* Низ: пользователь + выход, прижаты к нижней кромке */}
        <div className="mt-auto px-3 py-4 border-t border-line space-y-2">
          {company && (
            <div className="px-3 py-1">
              <p className="text-xs font-semibold text-content truncate">{company.name}</p>
              <p className="text-xs text-faint truncate">{company.email}</p>
            </div>
          )}
          <div className="flex items-center justify-between gap-2 px-1 pb-1">
            <LanguageSwitcher dropUp />
            <ThemeSwitcher />
          </div>
          <button
            onClick={() => { logout(); navigate('/login') }}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-muted hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/15 dark:hover:text-red-400 transition-colors"
          >
            <LogOut className="w-4 h-4" />{t('nav.logout')}
          </button>
        </div>
      </aside>

      <main className="relative z-10 flex-1 overflow-auto pt-14 md:pt-0">
        <div key={location.pathname} className="animate-fade-in">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
