import { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, CornerDownLeft, LayoutDashboard, Briefcase, Users, LayoutGrid, BarChart2, Sparkles, UserCog, Plug, Scale, Code2, CreditCard, Plus } from 'lucide-react'
import { useT } from '../i18n'

const NAV = [
  { to: '/',             icon: LayoutDashboard, key: 'nav.dashboard' },
  { to: '/jobs',         icon: Briefcase,       key: 'nav.jobs' },
  { to: '/candidates',   icon: Users,           key: 'nav.candidates' },
  { to: '/kanban',       icon: LayoutGrid,      key: 'nav.kanban' },
  { to: '/analytics',    icon: BarChart2,       key: 'nav.analytics' },
  { to: '/copilot',      icon: Sparkles,        key: 'nav.copilot' },
  { to: '/team',         icon: UserCog,         key: 'nav.team' },
  { to: '/integrations', icon: Plug,            key: 'nav.integrations' },
  { to: '/governance',   icon: Scale,           key: 'nav.governance' },
  { to: '/coding',       icon: Code2,           key: 'nav.coding' },
  { to: '/billing',      icon: CreditCard,      key: 'nav.billing' },
]

export default function CommandPalette() {
  const { t } = useT()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [active, setActive] = useState(0)
  const inputRef = useRef(null)

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault()
        setOpen((v) => !v)
      } else if (e.key === 'Escape') {
        setOpen(false)
      }
    }
    const onOpen = () => setOpen(true)
    window.addEventListener('keydown', onKey)
    window.addEventListener('open-command-palette', onOpen)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('open-command-palette', onOpen)
    }
  }, [])

  useEffect(() => {
    if (open) {
      setQ('')
      setActive(0)
      setTimeout(() => inputRef.current?.focus(), 20)
    }
  }, [open])

  const actions = useMemo(() => ([
    { id: 'create-job', icon: Plus, label: t('palette.createJob'), run: () => navigate('/jobs?new=1') },
  ]), [t, navigate])

  const navItems = NAV.map((n) => ({ ...n, label: t(n.key), run: () => navigate(n.to) }))

  const norm = (s) => (s || '').toLowerCase()
  const query = norm(q)
  const match = (item) => !query || norm(item.label).includes(query)

  const filteredActions = actions.filter(match)
  const filteredNav = navItems.filter(match)
  const flat = [...filteredActions, ...filteredNav]

  useEffect(() => { setActive(0) }, [q])

  function runAt(i) {
    const item = flat[i]
    if (!item) return
    item.run()
    setOpen(false)
  }

  function onInputKey(e) {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => Math.min(a + 1, flat.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)) }
    else if (e.key === 'Enter') { e.preventDefault(); runAt(active) }
  }

  if (!open) return null

  let idx = -1
  const renderItem = (item) => {
    idx += 1
    const i = idx
    const Icon = item.icon
    const isActive = i === active
    return (
      <button key={item.id || item.to} type="button"
        onMouseEnter={() => setActive(i)}
        onClick={() => runAt(i)}
        className={`flex items-center gap-3 w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors ${
          isActive ? 'bg-brand-600 text-white' : 'text-content hover:bg-surface-muted'
        }`}>
        <Icon className="w-4 h-4 shrink-0" />
        <span className="flex-1">{item.label}</span>
        {isActive && <CornerDownLeft className="w-3.5 h-3.5 opacity-70" />}
      </button>
    )
  }

  return (
    <div className="fixed inset-0 z-[9998] bg-black/40 backdrop-blur-sm flex items-start justify-center pt-[15vh] px-4"
      onMouseDown={() => setOpen(false)}>
      <div className="w-full max-w-lg bg-surface rounded-2xl shadow-2xl border border-line overflow-hidden animate-fade-in"
        onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3 px-4 border-b border-line">
          <Search className="w-4 h-4 text-faint shrink-0" />
          <input ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={onInputKey}
            placeholder={t('palette.placeholder')}
            className="flex-1 bg-transparent py-4 text-sm text-content placeholder:text-faint focus:outline-none" />
          <kbd className="text-[10px] text-faint border border-line rounded px-1.5 py-0.5">ESC</kbd>
        </div>
        <div className="max-h-80 overflow-y-auto p-2">
          {flat.length === 0 && (
            <p className="text-center text-sm text-muted py-8">{t('palette.empty')}</p>
          )}
          {filteredActions.length > 0 && (
            <>
              <p className="px-3 pt-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-faint">{t('palette.actions')}</p>
              {filteredActions.map(renderItem)}
            </>
          )}
          {filteredNav.length > 0 && (
            <>
              <p className="px-3 pt-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-faint">{t('palette.navigation')}</p>
              {filteredNav.map(renderItem)}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
