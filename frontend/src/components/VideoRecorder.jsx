import { useEffect, useRef, useState } from 'react'
import { Video, VideoOff, Loader2 } from 'lucide-react'
import { useT } from '../i18n'

export default function VideoRecorder({ interviewId, accessToken, onResponse, disabled }) {
  const { t } = useT()
  const [recording, setRecording] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [previewUrl, setPreviewUrl] = useState(null)
  const videoRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const streamRef = useRef(null)

  // Освобождаем object URL превью при его смене и при размонтировании,
  // а также останавливаем камеру, если компонент исчезает во время записи.
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [previewUrl])

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop())
    }
  }, [])

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720 },
        audio: true
      })
      streamRef.current = stream

      // Показать preview
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.play()
      }

      // Настроить MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'video/webm;codecs=vp8,opus'
      })
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data)
        }
      }

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        if (videoRef.current) {
          videoRef.current.srcObject = null
        }

        const blob = new Blob(chunksRef.current, { type: 'video/webm' })

        // Проверка размера (100MB)
        const sizeMB = blob.size / (1024 * 1024)
        if (sizeMB > 100) {
          alert(t('interview.videoTooLarge', { size: sizeMB.toFixed(1) }))
          return
        }

        // Показать preview записанного видео
        const url = URL.createObjectURL(blob)
        setPreviewUrl(url)

        await uploadVideo(blob)
      }

      mediaRecorder.start()
      setRecording(true)
    } catch (err) {
      console.error('Camera access error:', err)
      alert(t('interview.cameraDenied'))
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop()
    setRecording(false)
  }

  async function uploadVideo(blob) {
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('video', blob, 'video.webm')

      const response = await fetch(`/api/interviews/${interviewId}/video`, {
        method: 'POST',
        headers: { 'X-Interview-Token': accessToken || '' }, // SEC-1
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Upload failed')
      }

      const data = await response.json()

      // Очистить preview
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
        setPreviewUrl(null)
      }

      onResponse(data)
    } catch (err) {
      console.error('Video upload error:', err)
      alert(t('interview.videoError'))
    } finally {
      setUploading(false)
    }
  }

  // Очистка при размонтировании — см. useEffect выше.

  return (
    <div className="relative">
      {/* Preview видео */}
      {(recording || previewUrl) && (
        <div className="mb-3 rounded-lg overflow-hidden bg-black">
          <video
            ref={videoRef}
            className="w-full max-h-60 object-contain"
            src={previewUrl}
            muted={recording}
            playsInline
          />
        </div>
      )}

      {/* Кнопка записи */}
      <button
        type="button"
        onClick={recording ? stopRecording : startRecording}
        disabled={disabled || uploading}
        title={recording ? t('interview.stopVideoRecording') : t('interview.startVideoRecording')}
        className={`min-w-[44px] min-h-[44px] px-4 py-2 rounded-xl font-medium transition-all flex items-center justify-center gap-1 ${
          recording
            ? 'bg-red-500 hover:bg-red-600 text-white animate-pulse'
            : 'bg-surface-muted hover:bg-line text-muted'
        } ${(disabled || uploading) ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        {uploading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : recording ? (
          <VideoOff className="w-4 h-4" />
        ) : (
          <Video className="w-4 h-4" />
        )}
      </button>
    </div>
  )
}
