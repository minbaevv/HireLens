import { useEffect, useRef, useState } from 'react'
import { useParams, useLocation } from 'react-router-dom'
import axios from 'axios'
import api from '../api/client'
import { Send, Bot, User, CheckCircle, Mic, MicOff, Loader2 } from 'lucide-react'
import Spinner from '../components/Spinner'
import VideoRecorder from '../components/VideoRecorder'
import { useT } from '../i18n'
import LanguageSwitcher from '../components/LanguageSwitcher'
import Logo from '../components/Logo'
import InstallPrompt from '../components/InstallPrompt'

function Message({ role, content, delay = 0 }) {
  const isAI = role === 'ai'
  return (
    <div className={`flex gap-3 animate-slide-up ${isAI ? '' : 'flex-row-reverse'}`} style={{ animationDelay: `${delay}ms` }}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
        isAI ? 'bg-brand-600' : 'bg-surface-muted'
      }`}>
        {isAI ? <Bot className="w-4 h-4 text-white" /> : <User className="w-4 h-4 text-muted" />}
      </div>
      <div className={`max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
        isAI ? 'bg-surface border border-line text-content rounded-tl-sm shadow-sm'
             : 'bg-brand-600 text-white rounded-tr-sm'
      }`}>
        {content}
      </div>
    </div>
  )
}

export default function InterviewPage() {
  const { interviewId } = useParams()
  const location = useLocation()
  const { t } = useT()
  // SEC-1: токен доступа кандидата к интервью (выдаётся при старте на ApplyPage)
  const accessToken = sessionStorage.getItem(`interview_token_${interviewId}`) || ''
  const authHeaders = { 'X-Interview-Token': accessToken }
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [done, setDone] = useState(false)
  const bottomRef = useRef(null)

  // Голосовая запись
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])

  useEffect(() => {
    const first = location.state?.firstMessage
    if (first) {
      setMessages([{ role: 'ai', content: first }])
    } else {
      axios.get(`/api/interviews/${interviewId}`, { headers: authHeaders }).then(r => {
        setMessages(r.data.messages)
        if (r.data.status === 'completed') setDone(true)
      })
    }
  }, [interviewId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = e => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data)
      }

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        await sendVoice(blob)
      }

      mediaRecorder.start()
      setRecording(true)
    } catch {
      alert(t('interview.micDenied'))
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop()
    setRecording(false)
  }

  async function sendVoice(blob) {
    setTranscribing(true)
    try {
      const formData = new FormData()
      formData.append('audio', blob, 'voice.webm')
      const { data } = await api.post(`/interviews/${interviewId}/voice`, formData, {
        headers: { 'Content-Type': 'multipart/form-data', ...authHeaders },
      })
      if (data.transcribed_text) {
        setMessages(m => [...m, { role: 'user', content: data.transcribed_text }])
      }
      setMessages(m => [...m, { role: 'ai', content: data.message }])
      if (data.is_complete) setDone(true)
    } catch {
      setMessages(m => [...m, { role: 'ai', content: t('interview.voiceError') }])
    } finally {
      setTranscribing(false)
    }
  }

  function handleVideoResponse(data) {
    // Видео уже загружено и транскрибировано на бэкенде
    setMessages(m => [...m,
      { role: 'user', content: t('interview.videoSent') },
      { role: 'ai', content: data.message }
    ])
    if (data.is_complete) setDone(true)
  }

  async function sendMessage(e) {
    e.preventDefault()
    if (!input.trim() || sending) return
    const text = input.trim()
    setInput('')
    setMessages(m => [...m, { role: 'user', content: text }])
    setSending(true)
    try {
      const { data } = await axios.post(`/api/interviews/${interviewId}/message`, { content: text }, { headers: authHeaders })
      setMessages(m => [...m, { role: 'ai', content: data.message }])
      if (data.is_complete) setDone(true)
    } catch {
      setMessages(m => [...m, { role: 'ai', content: t('interview.genericError') }])
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="min-h-screen bg-canvas flex flex-col">
      <div
        className="bg-surface border-b border-line px-4 py-3 flex items-center gap-3"
        style={{ paddingTop: 'calc(0.75rem + env(safe-area-inset-top))' }}
      >
        <div className="w-9 h-9 bg-surface border border-line rounded-xl flex items-center justify-center shrink-0">
          <Logo className="w-6 h-6" title="HireLens" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-content truncate">{t('interview.headerTitle')}</p>
          <p className="text-xs text-faint">{done ? t('status.completed') : t('interview.inProgress')}</p>
        </div>
        <div className="ml-auto flex items-center gap-2 shrink-0">
          {done && (
            <div className="hidden sm:flex items-center gap-1.5 text-green-600 text-sm font-medium">
              <CheckCircle className="w-4 h-4" /> {t('status.completed')}
            </div>
          )}
          <InstallPrompt />
          <LanguageSwitcher alignRight />
        </div>
      </div>

      <div className="flex-1 overflow-auto px-4 py-6 max-w-2xl mx-auto w-full space-y-4">
        {messages.map((m, i) => <Message key={i} role={m.role} content={m.content} delay={Math.min(i * 60, 300)} />)}
        {sending && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div className="bg-surface border border-line rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
              <Spinner size="sm" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {done ? (
        <div
          className="bg-surface border-t border-line px-4 py-6 text-center"
          style={{ paddingBottom: 'calc(1.5rem + env(safe-area-inset-bottom))' }}
        >
          <CheckCircle className="w-10 h-10 text-green-500 mx-auto mb-3" />
          <p className="font-semibold text-content">{t('interview.doneTitle')}</p>
          <p className="text-sm text-muted mt-1">{t('interview.doneMessage')}</p>
        </div>
      ) : (
        <div
          className="bg-surface border-t border-line px-4 py-3"
          style={{ paddingBottom: 'calc(0.75rem + env(safe-area-inset-bottom))' }}
        >
          <form onSubmit={sendMessage} className="max-w-2xl mx-auto">
            <div className="flex gap-2">
              <input className="input flex-1 text-base sm:text-sm" placeholder={t('interview.inputPlaceholder')}
                value={input} onChange={e => setInput(e.target.value)}
                disabled={sending || recording || transcribing} autoFocus />

              <VideoRecorder
                interviewId={interviewId}
                accessToken={accessToken}
                onResponse={handleVideoResponse}
                disabled={sending || recording || transcribing}
              />

              <button
                type="button"
                onClick={recording ? stopRecording : startRecording}
                disabled={sending || transcribing}
                title={recording ? t('interview.stopRecording') : t('interview.startRecording')}
                className={`min-w-[44px] min-h-[44px] px-4 py-2 rounded-xl font-medium transition-all flex items-center justify-center gap-1 ${
                  recording
                    ? 'bg-red-500 hover:bg-red-600 text-white animate-pulse'
                    : 'bg-surface-muted hover:bg-line text-muted'
                }`}
              >
                {transcribing
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : recording
                    ? <MicOff className="w-4 h-4" />
                    : <Mic className="w-4 h-4" />}
              </button>

              <button type="submit" className="btn-primary min-w-[44px] min-h-[44px] px-4 justify-center"
                disabled={sending || !input.trim() || recording || transcribing}>
                <Send className="w-4 h-4" />
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
