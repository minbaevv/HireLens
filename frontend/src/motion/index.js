import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'

// Единая точка входа для motion-примитивов фронта.
// Все респектят prefers-reduced-motion (CSS глушит анимации глобально,
// а JS-примитивы дополнительно проверяют медиа-запрос).

// Переэкспорт существующего scroll-reveal, чтобы весь motion импортировался из одного места.
export { default as useReveal } from '../hooks/useReveal'

/** true, если пользователь просит уменьшить движение. */
export function prefersReducedMotion() {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

/**
 * usePageTransition — мягкий fade+slide при смене роута.
 * Использование:
 *   const page = usePageTransition()
 *   <div key={page.key} className={page.className}><Outlet /></div>
 * Ключ меняется при смене pathname → React перемонтирует блок → анимация проигрывается заново.
 */
export function usePageTransition() {
  const location = useLocation()
  return { key: location.pathname, className: 'animate-page' }
}

/**
 * useStagger — каскадное появление списка поверх IntersectionObserver.
 * Обёртка над тем же механизмом, что useReveal: вешает .is-visible на дочерние
 * элементы с атрибутом [data-stagger], добавляя нарастающий transition-delay.
 * Использование:
 *   const ref = useStagger()
 *   <div ref={ref}>{items.map(x => <div data-stagger className="reveal">…</div>)}</div>
 */
export function useStagger({ step = 60, threshold = 0.12, max = 600 } = {}, deps = []) {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const items = Array.from(el.querySelectorAll('[data-stagger]'))
    if (items.length === 0) return
    const reveal = () => {
      items.forEach((it, i) => {
        it.style.transitionDelay = `${Math.min(i * step, max)}ms`
        it.classList.add('is-visible')
      })
    }
    if (typeof IntersectionObserver === 'undefined') {
      reveal()
      return
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          reveal()
          observer.disconnect()
        }
      },
      { threshold },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [step, threshold, max, ...deps])
  return ref
}

/**
 * useCountUp — плавный счёт числа вверх при монтировании (для карточек статистики).
 * Анимирует только числовое значение через requestAnimationFrame. Уважает reduced-motion.
 */
export function useCountUp(target, { duration = 900 } = {}) {
  const [value, setValue] = useState(0)
  useEffect(() => {
    const end = Number(target) || 0
    if (prefersReducedMotion() || end === 0) {
      setValue(end)
      return
    }
    let raf
    let startTs = null
    const tick = (ts) => {
      if (startTs === null) startTs = ts
      const p = Math.min((ts - startTs) / duration, 1)
      const eased = 1 - Math.pow(1 - p, 3) // easeOutCubic
      setValue(Math.round(end * eased))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, duration])
  return value
}
