import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CalendarPlus, Video, Trash2, Clock } from 'lucide-react'
import api from '../api/client'
import Spinner from './Spinner'
import { useT } from '../i18n'
import { useAuth } from '../hooks/useAuth'
import { fmtDateTime, toInputValue, inputValueToISO, APP_TIMEZONE } from '../utils/datetime'

function toLocalInputValue(d) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export default function SchedulingCard({ candidateId }) {
  const { canWrite } = useAuth()
  const { t } = useT()
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState(null) // { enabled, connected, email }
  const [items, setItems] = useState([])
  const [when, setWhen] = useState('')
  const [duration, setDuration] = useState(60)
  const [notes, setNotes] = useState('')
  const [invite, setInvite] = useState(true)
  const [slots, setSlots] = useState([])
  const [loadingSlots, setLoadingSlots] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function load() {
    setLoading(true)
    try {
      const st = await api.get('/integrations/google/status')
      setStatus(st.data)
      if (st.data?.connected) {
        const sc = await api.get('/integrations/google/scheduled', { params: { candidate_id: candidateId } })
        setItems(sc.data || [])
      } else {
        setItems([])
      }
    } catch (err) {
      setError(err.response?.data?.detail || t('scheduling.error'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [candidateId])

  async function suggest() {
    setLoadingSlots(true)
    setError('')
    try {
      const { data } = await api.get('/integrations/google/free-slots', { params: { days: 7, duration: Number(duration) } })
      setSlots(data || [])
    } catch (err) {
      setError(err.response?.data?.detail || t('scheduling.error'))
    } finally {
      setLoadingSlots(false)
    }
  }

  async function submit(e) {
    e.preventDefault()
    if (!when) return
    setSubmitting(true)
    setError('')
    try {
      await api.post('/integrations/google/schedule', {
        candidate_id: candidateId,
        start: inputValueToISO(when),
        duration_minutes: Number(duration),
        notes: notes || null,
        invite_candidate: invite,
      })
      setWhen(''); setNotes(''); setSlots([])
      await load()
    } catch (err) {
      setError(err.response?.data?.detail || t('scheduling.error'))
    } finally {
      setSubmitting(false)
    }
  }

  async function cancel(id) {
    if (!window.confirm(t('scheduling.cancelConfirm'))) return
    setError('')
    try {
      await api.delete(`/integrations/google/scheduled/${id}`)
      await load()
    } catch (err) {
      setError(err.response?.data?.detail || t('scheduling.error'))
    }
  }

  if (loading) {
    return (
      <div className="card p-6 flex justify-center"><Spinner /></div>
    )
  }

  return (
    <div className="card p-6 space-y-4">
      <div className="flex items-center gap-2">
        <CalendarPlus className="w-4 h-4 text-brand-600" />
        <h2 className="text-sm font-semibold text-content">{t('scheduling.title')}</h2>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 dark:bg-red-500/10 dark:border-red-500/30 dark:text-red-300 text-sm px-4 py-3 rounded-lg">{error}</div>
      )}

      {!status?.enabled && (
        <p className="text-sm text-muted">{t('scheduling.notConfigured')}</p>
      )}

      {status?.enabled && !status?.connected && (
        <div className="text-sm text-muted space-y-2">
          <p>{t('scheduling.notConnected')}</p>
          <Link to="/integrations" className="btn-secondary inline-flex">{t('scheduling.goConnect')}</Link>
        </div>
      )}

      {canWrite && status?.enabled && status?.connected && (
        <>
          <p className="text-sm text-muted">{t('scheduling.hint')}</p>
          <p className="text-xs text-faint">🕒 {APP_TIMEZONE} (UTC+6)</p>
          <form onSubmit={submit} className="space-y-3">
            <div className="flex flex-wrap gap-3">
              <input
                type="datetime-local"
                value={when}
                onChange={(e) => setWhen(e.target.value)}
                className="input"
                required
              />
              <select value={duration} onChange={(e) => setDuration(Number(e.target.value))} className="input">
                <option value={30}>30 {t('scheduling.min')}</option>
                <option value={45}>45 {t('scheduling.min')}</option>
                <option value={60}>60 {t('scheduling.min')}</option>
              </select>
              <button type="button" onClick={suggest} className="btn-secondary inline-flex items-center gap-1" disabled={loadingSlots}>
                <Clock className="w-4 h-4" /> {t('scheduling.suggest')}
              </button>
            </div>

            {loadingSlots && <Spinner size="sm" />}
            {slots.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {slots.map((s) => (
                  <button
                    key={s.start}
                    type="button"
                    onClick={() => setWhen(toInputValue(new Date(s.start)))}
                    className="btn-secondary text-xs"
                  >
                    {fmtDateTime(s.start)}
                  </button>
                ))}
              </div>
            )}

            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={t('scheduling.notesPlaceholder')}
              rows={2}
              className="input w-full"
            />

            <label className="flex items-center gap-2 text-sm text-muted">
              <input type="checkbox" checked={invite} onChange={(e) => setInvite(e.target.checked)} />
              {t('scheduling.inviteCandidate')}
            </label>

            <button type="submit" disabled={submitting || !when} className="btn-primary inline-flex items-center gap-1">
              {submitting ? <Spinner size="sm" /> : <><CalendarPlus className="w-4 h-4" /> {t('scheduling.schedule')}</>}
            </button>
          </form>

          {items.length > 0 && (
            <ul className="space-y-2 pt-3 border-t border-border">
              {items.map((it) => (
                <li key={it.id} className="flex items-center justify-between gap-3 text-sm">
                  <div className="flex flex-col">
                    <span className={it.status === 'cancelled' ? 'text-muted line-through' : 'text-content'}>
                      {it.start_time ? fmtDateTime(it.start_time) : '—'}
                    </span>
                    {it.status !== 'cancelled' && it.meet_link && (
                      <a href={it.meet_link} target="_blank" rel="noreferrer" className="text-brand-600 inline-flex items-center gap-1">
                        <Video className="w-4 h-4" /> {t('scheduling.joinMeet')}
                      </a>
                    )}
                    {it.status === 'cancelled' && (
                      <span className="text-xs text-muted">{t('scheduling.cancelled')}</span>
                    )}
                  </div>
                  {it.status !== 'cancelled' && (
                    <button type="button" onClick={() => cancel(it.id)} className="text-red-600 hover:text-red-700 shrink-0" title={t('scheduling.cancel')}>
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  )
}
