import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Rocket, Check, ChevronRight, X } from 'lucide-react'
import { useT } from '../i18n'

// Персистентный чеклист быстрого старта на дашборде.
// Шаги отмечаются автоматически по реальным данным аналитики.
export default function OnboardingChecklist({ stats }) {
  const { t } = useT()
  const navigate = useNavigate()
  const [hidden, setHidden] = useState(() => localStorage.getItem('checklist_done') === '1')

  const steps = [
    { key: 'step1', done: (stats?.total_jobs ?? 0) > 0,       to: '/jobs' },
    { key: 'step2', done: (stats?.total_candidates ?? 0) > 0, to: '/jobs' },
    { key: 'step3', done: (stats?.hired_count ?? 0) > 0,      to: '/kanban' },
  ]
  const doneCount = steps.filter((s) => s.done).length
  const allDone = doneCount === steps.length

  // Скрываем, если закрыли вручную или всё выполнено.
  if (hidden || allDone) return null

  function dismiss() {
    localStorage.setItem('checklist_done', '1')
    setHidden(true)
  }

  return (
    <div className="card p-6 mb-8 relative overflow-hidden animate-fade-in">
      <div className="absolute inset-0 bg-gradient-to-r from-brand-50/60 to-transparent dark:from-brand-500/10 pointer-events-none" />
      <button onClick={dismiss} aria-label={t('checklist.dismiss')}
        className="absolute top-3 right-3 p-1.5 rounded-lg text-faint hover:text-muted hover:bg-surface-muted transition-colors">
        <X className="w-4 h-4" />
      </button>
      <div className="relative">
        <div className="flex items-center gap-3 mb-1">
          <div className="inline-flex p-2 rounded-xl bg-brand-100 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
            <Rocket className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-content">{t('checklist.title')}</h3>
            <p className="text-xs text-muted">{t('checklist.subtitle')}</p>
          </div>
          <span className="ml-auto mr-8 text-sm font-semibold text-brand-600 dark:text-brand-300">{doneCount}/{steps.length}</span>
        </div>

        <div className="h-1.5 w-full rounded-full bg-surface-muted my-4 overflow-hidden">
          <div className="h-full bg-brand-600 transition-all duration-500" style={{ width: `${(doneCount / steps.length) * 100}%` }} />
        </div>

        <div className="space-y-1">
          {steps.map((s, i) => (
            <button key={s.key} onClick={() => navigate(s.to)}
              className="flex items-center gap-3 w-full text-left p-2.5 rounded-lg hover:bg-surface-muted transition-colors group">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 text-xs font-semibold ${
                s.done ? 'bg-green-100 text-green-600 dark:bg-green-500/15 dark:text-green-300' : 'bg-surface-muted text-muted border border-line'
              }`}>
                {s.done ? <Check className="w-3.5 h-3.5" /> : i + 1}
              </div>
              <span className={`text-sm flex-1 ${s.done ? 'text-muted line-through' : 'text-content font-medium'}`}>
                {t(`checklist.${s.key}`)}
              </span>
              {!s.done && <ChevronRight className="w-4 h-4 text-faint group-hover:text-muted transition-colors" />}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
