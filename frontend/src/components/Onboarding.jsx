import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Briefcase, Link, Users, ChevronRight, Sparkles } from 'lucide-react'

const STEPS = [
  {
    icon: Briefcase,
    color: 'bg-blue-100 text-blue-600 dark:bg-blue-500/15 dark:text-blue-300',
    title: 'Создай первую вакансию',
    desc: 'Опиши должность и требования. AI будет задавать вопросы на основе этих данных.',
  },
  {
    icon: Link,
    color: 'bg-brand-100 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300',
    title: 'Отправь ссылку кандидатам',
    desc: 'Каждая вакансия получает уникальную ссылку. Отправь её в Telegram, hh.kg или по email.',
  },
  {
    icon: Users,
    color: 'bg-green-100 text-green-600 dark:bg-green-500/15 dark:text-green-300',
    title: 'Получай результаты',
    desc: 'Кандидаты проходят AI-интервью самостоятельно. Ты получаешь оценку, резюме и рекомендацию по каждому.',
  },
]

export default function Onboarding({ onDismiss }) {
  const [step, setStep] = useState(0)
  const navigate = useNavigate()

  function handleFinish() {
    onDismiss()
    navigate('/jobs')
  }

  const isLast = step === STEPS.length - 1

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-surface rounded-2xl shadow-2xl w-full max-w-md p-8">

        {/* Заголовок */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300 px-3 py-1 rounded-full text-sm font-medium mb-4">
            <Sparkles className="w-4 h-4" />
            Добро пожаловать в HireLens!
          </div>
          <h2 className="text-xl font-bold text-content">Начнём за 3 простых шага</h2>
          <p className="text-muted text-sm mt-1">Автоматизируй найм с помощью AI</p>
        </div>

        {/* Шаги */}
        <div className="space-y-3 mb-8">
          {STEPS.map((s, i) => {
            const Icon = s.icon
            const isActive = i === step
            const isDone = i < step
            return (
              <div key={i} className={`flex items-start gap-4 p-4 rounded-xl transition-all ${
                isActive ? 'bg-surface-muted border border-line' : 'opacity-50'
              }`}>
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                  isDone ? 'bg-green-100 text-green-600 dark:bg-green-500/15 dark:text-green-300' : s.color
                }`}>
                  {isDone
                    ? <span className="text-lg">✓</span>
                    : <Icon className="w-5 h-5" />}
                </div>
                <div>
                  <p className={`text-sm font-semibold ${
                    isActive ? 'text-content' : 'text-muted'
                  }`}>
                    <span className="text-xs text-faint mr-1">{i + 1}.</span>
                    {s.title}
                  </p>
                  {isActive && <p className="text-xs text-muted mt-1">{s.desc}</p>}
                </div>
              </div>
            )
          })}
        </div>

        {/* Прогресс-бар */}
        <div className="flex gap-1.5 mb-6">
          {STEPS.map((_, i) => (
            <div key={i} className={`h-1.5 flex-1 rounded-full transition-all ${
              i <= step ? 'bg-brand-600' : 'bg-surface-muted'
            }`} />
          ))}
        </div>

        {/* Кнопки */}
        <div className="flex gap-3">
          <button
            onClick={onDismiss}
            className="flex-1 btn-secondary text-sm"
          >
            Пропустить
          </button>
          <button
            onClick={isLast ? handleFinish : () => setStep(s => s + 1)}
            className="flex-1 btn-primary text-sm flex items-center justify-center gap-2"
          >
            {isLast ? 'Создать вакансию →' : (
              <>Далее <ChevronRight className="w-4 h-4" /></>
            )}
          </button>
        </div>

      </div>
    </div>
  )
}
