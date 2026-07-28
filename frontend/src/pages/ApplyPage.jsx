import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import axios from 'axios'
import { Bot, Upload, FileText, Info, CheckCircle2 } from 'lucide-react'
import Spinner from '../components/Spinner'
import LanguageSwitcher from '../components/LanguageSwitcher'
import Logo from '../components/Logo'
import AnimatedBackground from '../components/AnimatedBackground'
import { useT } from '../i18n'

function RichText({ text }) {
  const lines = String(text || '').split(/\r?\n/).map(l => l.trim()).filter(Boolean)
  if (lines.length === 0) return <p className="text-sm text-muted italic">—</p>
  return (
    <div className="space-y-1.5">
      {lines.map((line, i) => {
        const m = line.match(/^[-•*–—]\s*(.+)/)
        if (m) return (
          <div key={i} className="flex items-start gap-2 text-sm text-muted">
            <CheckCircle2 className="w-4 h-4 mt-0.5 text-brand-500 shrink-0" />
            <span>{m[1]}</span>
          </div>
        )
        return <p key={i} className="text-sm text-muted">{line}</p>
      })}
    </div>
  )
}

// iPhone отдаёт снимки в HEIC и размером 3-5 МБ — такое фото не доезжало до сервера.
// Пережимаем в браузере в JPEG до 1280px (~200 КБ). Если что-то пошло не так —
// отправляем исходный файл, чтобы не ломать подачу заявки.
function preparePhoto(file) {
  return new Promise(resolve => {
    try {
      const url = URL.createObjectURL(file)
      const img = new Image()
      img.onload = () => {
        try {
          const max = 1280
          const scale = Math.min(1, max / Math.max(img.width, img.height))
          const canvas = document.createElement('canvas')
          canvas.width = Math.round(img.width * scale)
          canvas.height = Math.round(img.height * scale)
          canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height)
          canvas.toBlob(blob => {
            URL.revokeObjectURL(url)
            resolve(blob ? new File([blob], 'photo.jpg', { type: 'image/jpeg' }) : file)
          }, 'image/jpeg', 0.85)
        } catch (e) {
          URL.revokeObjectURL(url)
          resolve(file)
        }
      }
      img.onerror = () => { URL.revokeObjectURL(url); resolve(file) }
      img.src = url
    } catch (e) {
      resolve(file)
    }
  })
}

export default function ApplyPage() {
  const { token } = useParams()
  const navigate = useNavigate()
  const { t, setLang } = useT()
  const [job, setJob] = useState(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ name: '', email: '', phone: '', resume_text: '' })
  const [file, setFile] = useState(null)
  const [photo, setPhoto] = useState(null)
  const [useFile, setUseFile] = useState(false)

  useEffect(() => {
    axios.get(`/api/apply/${token}`)
      .then(r => {
        setJob(r.data)
        // Язык интерфейса = язык вакансии (кандидат может переключить вручную)
        if (r.data.language) setLang(r.data.language)
      })
      .catch(() => setJob(null))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const fd = new FormData()
      fd.append('name', form.name)
      fd.append('email', form.email)
      if (form.phone) fd.append('phone', form.phone)
      if (useFile && file) fd.append('resume_file', file)
      else if (form.resume_text) fd.append('resume_text', form.resume_text)
      if (photo) fd.append('photo_file', await preparePhoto(photo))
      const { data } = await axios.post(`/api/apply/${token}`, fd)
      const iv = await axios.post(`/api/interviews/${data.id}/start`)
      // SEC-1: токен доступа к интервью — без него бэкенд отклонит запросы
      sessionStorage.setItem(`interview_token_${iv.data.interview_id}`, iv.data.access_token)
      navigate(`/interview/${iv.data.interview_id}`, {
        state: { firstMessage: iv.data.message, secondsRemaining: iv.data.seconds_remaining, companyLogoUrl: job.company_logo_url, companyName: job.company_name }
      })
    } catch (err) {
      // 413 приходит от nginx HTML-страницей — detail в нём нет, нужен свой текст.
      const detail = err.response?.data?.detail
      if (typeof detail === 'string' && detail) setError(detail)
      else if (err.response?.status === 413) setError(t('apply.tooLarge'))
      else setError(t('apply.error'))
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <div className="flex items-center justify-center min-h-screen"><Spinner size="lg" /></div>

  if (!job) return (
    <div className="min-h-screen bg-canvas flex items-center justify-center">
      <div className="text-center">
        <p className="text-2xl font-bold text-content mb-2">{t('apply.notFound')}</p>
        <p className="text-muted">{t('apply.notFoundHint')}</p>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center p-4">
      <AnimatedBackground variant="auth" />
      <div className="relative z-10 w-full max-w-lg">
        <div className="flex justify-end mb-4">
          <LanguageSwitcher alignRight />
        </div>
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-surface border border-line rounded-2xl mb-4 shadow-lg overflow-hidden">
            {job.company_logo_url
              ? <img src={job.company_logo_url} alt={job.company_name || ''} className="w-full h-full object-contain" />
              : <Logo className="w-9 h-9" title="HireLens" />}
          </div>
          <h1 className="page-title">{job.title}</h1>
          <p className="page-subtitle">{t('apply.subtitle')}</p>
        </div>
        <div className="card p-5 mb-5">
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-content mb-2"><Info className="w-4 h-4 text-brand-500" />{t('apply.about')}</h2>
          <div className="mb-4"><RichText text={job.description} /></div>
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-content mb-2"><CheckCircle2 className="w-4 h-4 text-brand-500" />{t('apply.requirements')}</h2>
          <RichText text={job.requirements} />
        </div>
        <div className="card p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-content mb-1.5">{t('apply.name')}</label>
              <input className="input" placeholder={t('apply.namePlaceholder')}
                value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
            </div>
            <div>
              <label className="block text-sm font-medium text-content mb-1.5">Email</label>
              <input type="email" className="input" placeholder="ivan@example.com"
                value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} required />
            </div>
            <div>
              <label className="block text-sm font-medium text-content mb-1.5">{t('apply.phone')}</label>
              <input type="tel" className="input" placeholder={t('apply.phonePlaceholder')}
                value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))} />
              <p className="text-xs text-faint mt-1">{t('apply.phoneHint')}</p>
            </div>
            <div>
              <div className="flex items-center gap-4 mb-3">
                <label className="text-sm font-medium text-content">{t('apply.resume')}</label>
                <div className="flex rounded-lg border border-line overflow-hidden text-xs">
                  <button type="button" onClick={() => setUseFile(false)}
                    className={`px-3 py-1.5 font-medium transition-colors ${
                      !useFile ? 'bg-brand-600 text-white' : 'bg-surface text-muted hover:bg-surface-muted'
                    }`}>
                    <FileText className="w-3 h-3 inline mr-1" />{t('apply.text')}
                  </button>
                  <button type="button" onClick={() => setUseFile(true)}
                    className={`px-3 py-1.5 font-medium transition-colors ${
                      useFile ? 'bg-brand-600 text-white' : 'bg-surface text-muted hover:bg-surface-muted'
                    }`}>
                    <Upload className="w-3 h-3 inline mr-1" />{t('apply.file')}
                  </button>
                </div>
              </div>
              {useFile ? (
                <label className="flex flex-col items-center justify-center w-full h-28 border-2 border-dashed border-line rounded-lg cursor-pointer hover:border-brand-400 hover:bg-brand-50 dark:hover:bg-brand-500/10 transition-colors">
                  <Upload className="w-6 h-6 text-faint mb-2" />
                  <span className="text-sm text-muted">{file ? file.name : t('apply.fileHint')}</span>
                  <input type="file" className="hidden" accept=".pdf,.txt" onChange={e => setFile(e.target.files[0])} />
                </label>
              ) : (
                <textarea className="input min-h-[100px] resize-none"
                  placeholder={t('apply.resumePlaceholder')}
                  value={form.resume_text} onChange={e => setForm(f => ({ ...f, resume_text: e.target.value }))} />
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-content mb-1.5">{t('apply.photo')}</label>
              <label className="flex items-center gap-3 w-full px-4 py-3 border-2 border-dashed border-line rounded-lg cursor-pointer hover:border-brand-400 hover:bg-brand-50 dark:hover:bg-brand-500/10 transition-colors">
                <Upload className="w-5 h-5 text-faint shrink-0" />
                <span className="text-sm text-muted truncate">{photo ? photo.name : t('apply.photoHint')}</span>
                <input type="file" className="hidden" accept="image/*" onChange={e => setPhoto(e.target.files[0])} />
              </label>
            </div>
            {error && <div className="bg-red-50 border border-red-200 text-red-700 dark:bg-red-500/10 dark:border-red-500/30 dark:text-red-300 text-sm px-4 py-3 rounded-lg">{error}</div>}
            <button type="submit" className="btn-primary w-full justify-center py-3" disabled={submitting}>
              {submitting ? <><Spinner size="sm" /> {t('apply.submitting')}</> : t('apply.submit')}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
