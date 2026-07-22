import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Code2, Copy, Check } from 'lucide-react'
import api from '../api/client'
import { useT } from '../i18n'
import { useAuth } from '../hooks/useAuth'

export default function CodingCard({ candidateId }) {
  const { canWrite } = useAuth()
  const { t } = useT()
  const [challenges, setChallenges] = useState([])
  const [subs, setSubs] = useState([])
  const [selected, setSelected] = useState('')
  const [assigning, setAssigning] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [copied, setCopied] = useState(null)
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      const [c, s] = await Promise.all([
        api.get('/coding/challenges'),
        api.get('/coding/submissions', { params: { candidate_id: candidateId } }),
      ])
      setChallenges(c.data)
      setSubs(s.data)
    } catch (err) {
      // карточка не критична — тихо игнорируем
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [candidateId])

  async function assign() {
    if (!selected) return
    setAssigning(true); setError(''); setNotice('')
    try {
      await api.post('/coding/assign', { challenge_id: Number(selected), candidate_id: Number(candidateId) })
      setNotice(t('coding.assignedOk'))
      setSelected('')
      await load()
    } catch (err) {
      if (err.response?.status === 403) setError(t('coding.forbidden'))
      else setError(err.response?.data?.detail || t('coding.errorSave'))
    } finally { setAssigning(false) }
  }

  function copyLink(tokenValue) {
    const url = `${window.location.origin}/coding/${tokenValue}`
    navigator.clipboard?.writeText(url)
    setCopied(tokenValue)
    setTimeout(() => setCopied(null), 1500)
  }

  function statusLabel(st) {
    if (st === 'submitted') return t('coding.stSubmitted')
    if (st === 'reviewed') return t('coding.stReviewed')
    return t('coding.stAssigned')
  }

  if (loading) return null

  return (
    <div className="card p-6 mb-6">
      <div className="flex items-center gap-2 mb-1">
        <Code2 className="w-5 h-5 text-brand-600" />
        <h2 className="font-semibold text-content">{t('coding.cardTitle')}</h2>
      </div>
      <p className="text-xs text-faint mb-4">{t('coding.cardHint')}</p>

      {challenges.length === 0 ? (
        <p className="text-sm text-muted">
          {t('coding.noChallengesToAssign')}{' '}
          <Link to="/coding" className="text-brand-600 hover:underline">{t('coding.manageLink')}</Link>
        </p>
      ) : canWrite ? (
        <div className="flex flex-col sm:flex-row gap-2 mb-4">
          <select className="input flex-1" value={selected} onChange={e => setSelected(e.target.value)}>
            <option value="">{t('coding.selectChallenge')}</option>
            {challenges.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
          </select>
          <button type="button" onClick={assign} disabled={!selected || assigning} className="btn-primary shrink-0">
            {assigning ? t('coding.assigning') : t('coding.assign')}
          </button>
        </div>
      ) : null}

      {error && <p className="text-sm text-red-500 mb-2">{error}</p>}
      {notice && <p className="text-sm text-green-600 mb-2">{notice}</p>}

      {subs.length === 0 ? (
        <p className="text-sm text-faint">{t('coding.noAssigned')}</p>
      ) : (
        <div className="space-y-2">
          {subs.map(s => {
            const title = challenges.find(c => c.id === s.challenge_id)?.title || ('#' + s.challenge_id)
            return (
              <div key={s.id} className="flex items-center justify-between gap-2 text-sm border border-line rounded-lg px-3 py-2">
                <div className="min-w-0">
                  <p className="text-content truncate">{title}</p>
                  <p className="text-xs text-faint">
                    {statusLabel(s.status)}
                    {s.auto_score != null && ` · ${t('coding.colAuto')}: ${s.auto_score}`}
                    {s.manual_score != null && ` · ${t('coding.colFinal')}: ${s.manual_score}`}
                  </p>
                </div>
                <button type="button" onClick={() => copyLink(s.access_token)} className="btn-secondary shrink-0 inline-flex items-center gap-1 text-xs">
                  {copied === s.access_token ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied === s.access_token ? t('coding.linkCopied') : t('coding.copyLink')}
                </button>
              </div>
            )
          })}
          <p className="text-xs text-faint mt-1">{t('coding.candidateLinkHint')}</p>
        </div>
      )}
    </div>
  )
}
