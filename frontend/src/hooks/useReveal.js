import { useEffect, useRef } from 'react'

/**
 * Scroll-reveal через IntersectionObserver.
 * Использование: <div ref={useReveal()} className="reveal">…</div>
 * При входе элемента во вьюпорт добавляется .is-visible (см. index.css).
 * Уважает prefers-reduced-motion (CSS отключает transition).
 */
export default function useReveal(threshold = 0.15) {
  const ref = useRef(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (typeof IntersectionObserver === 'undefined') {
      el.classList.add('is-visible')
      return
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add('is-visible')
          observer.disconnect()
        }
      },
      { threshold },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [threshold])

  return ref
}
