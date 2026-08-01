import { useEffect, useState } from 'react'
import { MessageSquare, Trash2, Plus } from 'lucide-react'
import api from '../api/client'
import Spinner from './Spinner'
import { useAuth } from '../hooks/useAuth'

const QUICK_REASONS = [
  'Кандидат отказался сам',
  'Не устроила зарплата',
  'Не вышел на связь',
  'Неудобный график',
  'Не пришёл на собеседование',
]

const MAX_LENGTH = 1000

function formatWhen(value) {
  if (!value) return ''
  const d = new Date(value)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function CandidateComments({ candidateId }) {
  const { canWrite } = useAuth()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [text, setText] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function load() {
    try {
      const { data } = await api.get(`/candidates/${candidateId}/comments`)
      setItems(Array.isArray(data.items) ? data.items : [])
    } catch (e) {
      setError('Не удалось загрузить комментарии')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setLoading(true)
    load()
     
  }, [candidateId])

  function addQuick(reason) {
    setText(prev => (prev.trim() ? prev.trim() + '. ' + reason : reason))
  }

  async function save() {
    const value = text.trim()
    if (!value || saving) return
    setSaving(true)
    setError('')
    try {
      const { data } = await api.post(`/candidates/${candidateId}/comments`, { text: value })
      setItems(prev => [data, ...prev])
      setText('')
    } catch (e) {
      setError('Не удалось сохранить комментарий')
    } finally {
      setSaving(false)
    }
  }

  async function remove(commentId) {
    if (!window.confirm('Удалить комментарий?')) return
    try {
      await api.delete(`/candidates/${candidateId}/comments/${commentId}`)
      setItems(prev => prev.filter(c => c.id !== commentId))
    } catch (e) {
      setError('Не удалось удалить комментарий')
    }
  }

  return (
    <div className="card p-6 mb-4">
      <div className="flex items-center gap-2 mb-1">
        <MessageSquare className="w-4 h-4 text-brand-600" />
        <h2 className="section-title">Комментарии</h2>
        {items.length > 0 && (
          <span className="text-xs text-faint">({items.length})</span>
        )}
      </div>
      <p className="text-xs text-faint mb-4">
        Заметки о кандидате: договорённости, впечатления, причина отказа. Видны всей команде.
      </p>

      {error && (
        <div className="mb-3 text-sm text-red-600">{error}</div>
      )}

      {canWrite && (
        <div className="mb-4">
          <textarea
            className="input min-h-[72px] mb-2"
            maxLength={MAX_LENGTH}
            placeholder="Например: подходит по опыту, но отказалась — нашла работу ближе к дому"
            value={text}
            onChange={e => setText(e.target.value)}
          />
          <div className="flex flex-wrap gap-2 mb-3">
            {QUICK_REASONS.map(reason => (
              <button
                key={reason}
                type="button"
                onClick={() => addQuick(reason)}
                className="px-2.5 py-1 text-xs font-medium rounded-lg border border-line text-muted bg-surface hover:bg-surface-muted transition-colors"
              >
                {reason}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <button onClick={save} disabled={!text.trim() || saving} className="btn-primary">
              <Plus className="w-4 h-4" /> Добавить
            </button>
            <span className="text-xs text-faint">{text.length} / {MAX_LENGTH}</span>
          </div>
        </div>
      )}

      {loading ? (
        <Spinner />
      ) : items.length === 0 ? (
        <p className="text-sm text-faint">Пока нет комментариев.</p>
      ) : (
        <ul className="space-y-3">
          {items.map(item => (
            <li key={item.id} className="border border-line rounded-lg p-3 bg-surface">
              <div className="flex items-center justify-between gap-3 mb-1">
                <span className="text-xs font-medium text-muted">{item.author_name}</span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-faint">{formatWhen(item.created_at)}</span>
                  {canWrite && (
                    <button
                      type="button"
                      onClick={() => remove(item.id)}
                      title="Удалить"
                      className="text-faint hover:text-red-600 transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
              <p className="text-sm whitespace-pre-wrap">{item.text}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
