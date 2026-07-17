import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Sparkles, Send, User, Bot } from 'lucide-react'
import api from '../api/client'
import Spinner from '../components/Spinner'
import { useT } from '../i18n'

function ReferencedChips({ candidates, label }) {
  if (!candidates?.length) return null
  return (
    <div className="mt-3 pt-3 border-t border-line">
      <p className="text-xs text-faint mb-2">{label}</p>
      <div className="flex flex-wrap gap-2">
        {candidates.map(c => (
          <Link
            key={c.id}
            to={`/candidates/${c.id}`}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-brand-50 text-brand-700 text-xs font-medium hover:bg-brand-100 transition-colors"
          >
            {c.name}
            {c.score != null && <span className="text-brand-400">· {Math.round(c.score)}</span>}
          </Link>
        ))}
      </div>
    </div>
  )
}

export default function CopilotPage() {
  const { t } = useT()
  const [messages, setMessages] = useState([]) // {role, content, referenced?}
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const send = async (text) => {
    const message = (text ?? input).trim()
    if (!message || loading) return

    const history = messages.map(m => ({ role: m.role, content: m.content }))
    setMessages(prev => [...prev, { role: 'user', content: message }])
    setInput('')
    setLoading(true)

    try {
      const { data } = await api.post('/copilot/chat', { message, history })
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        referenced: data.referenced_candidates,
      }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: t('copilot.error'), error: true }])
    } finally {
      setLoading(false)
    }
  }

  const onSubmit = (e) => {
    e.preventDefault()
    send()
  }

  const suggestions = [t('copilot.suggest1'), t('copilot.suggest2'), t('copilot.suggest3')]

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-8 pt-8 pb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-content">{t('copilot.title')}</h1>
            <p className="text-sm text-muted">{t('copilot.subtitle')}</p>
          </div>
        </div>
        {messages.length > 0 && (
          <button
            onClick={() => setMessages([])}
            className="text-sm text-faint hover:text-muted transition-colors"
          >
            {t('copilot.clear')}
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto px-8 pb-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto">
            <div className="w-14 h-14 rounded-2xl bg-brand-50 text-brand-500 flex items-center justify-center mb-4">
              <Sparkles className="w-7 h-7" />
            </div>
            <h2 className="text-lg font-semibold text-content">{t('copilot.emptyTitle')}</h2>
            <p className="text-sm text-muted mt-1 mb-6">{t('copilot.emptyHint')}</p>
            <div className="flex flex-col gap-2 w-full">
              {suggestions.map((s, i) => (
                <button
                  key={i}
                  onClick={() => send(s)}
                  className="text-left text-sm px-4 py-2.5 rounded-xl border border-line text-content hover:border-brand-300 hover:bg-brand-50 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-4">
            {messages.map((m, i) => (
              <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : ''}`}>
                {m.role === 'assistant' && (
                  <div className="w-8 h-8 shrink-0 rounded-lg bg-brand-50 text-brand-600 flex items-center justify-center">
                    <Bot className="w-4 h-4" />
                  </div>
                )}
                <div className={`rounded-2xl px-4 py-3 max-w-[80%] ${
                  m.role === 'user'
                    ? 'bg-brand-600 text-white'
                    : m.error
                      ? 'bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-300'
                      : 'bg-surface border border-line text-content'
                }`}>
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">{m.content}</p>
                  {m.role === 'assistant' && !m.error && (
                    <ReferencedChips candidates={m.referenced} label={t('copilot.referenced')} />
                  )}
                </div>
                {m.role === 'user' && (
                  <div className="w-8 h-8 shrink-0 rounded-lg bg-surface-muted text-muted flex items-center justify-center">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="flex gap-3">
                <div className="w-8 h-8 shrink-0 rounded-lg bg-brand-50 text-brand-600 flex items-center justify-center">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="rounded-2xl px-4 py-3 bg-surface border border-line flex items-center gap-2">
                  <Spinner size="sm" />
                  <span className="text-sm text-faint">{t('copilot.thinking')}</span>
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="px-8 py-4 border-t border-line bg-surface">
        <form onSubmit={onSubmit} className="max-w-3xl mx-auto flex gap-2">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder={t('copilot.placeholder')}
            disabled={loading}
            className="flex-1 px-4 py-2.5 rounded-xl border border-line bg-surface text-content text-sm focus:outline-none focus:border-brand-400 disabled:bg-surface-muted"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-2.5 rounded-xl bg-brand-600 text-white text-sm font-medium flex items-center gap-2 hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-4 h-4" />
            <span className="hidden sm:inline">{t('copilot.send')}</span>
          </button>
        </form>
      </div>
    </div>
  )
}
