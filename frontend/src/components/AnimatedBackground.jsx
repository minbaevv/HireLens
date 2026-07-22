import { useEffect, useRef } from 'react'
import { useTheme } from '../theme'

/**
 * AnimatedBackground — живой фон-«объектив» HireLens.
 *
 * Метафора продукта: объектив/апертура, через который HR видит только
 * релевантных кандидатов, а шум остаётся размытым. Рифмуется с логотипом
 * (circuit-точки + дуга апертуры + scan). Не «частицы на тёмном».
 *
 * Слои (все на одном <canvas>):
 *   1. Тонкая сетка точек-данных — «шум», который система фильтрует
 *      (цвет из токена --color-faint, адаптируется под светлую/тёмную тему).
 *   2. 2–3 расфокусированных боке-пятна (cyan/blue из brand-палитры,
 *      низкая непрозрачность, медленный дрейф).
 *   3. Редкий диагональный scan-луч (перекликается с дугой апертуры).
 *
 * Производительность: один rAF, ≤ ~15 движущихся объектов, DPR ≤ 2, пауза
 * на скрытой вкладке (visibilitychange). Сетка собрана в Path2D — один fill
 * на кадр. prefers-reduced-motion → статичный мягкий градиент, без rAF.
 *
 * Пропсы:
 *   subtle — тихая версия для авторизованной части (Layout): без сетки и
 *            scan-луча, меньше и бледнее боке. По умолчанию false (лендинг).
 *
 * Презентационный слой: pointer-events-none, aria-hidden, z ниже контента.
 */
export default function AnimatedBackground({ subtle = false }) {
  const canvasRef = useRef(null)
  // Тема нужна лишь как триггер переинициализации палитры точек.
  const { isDark } = useTheme()

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const reduce =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    const dpr = Math.min(window.devicePixelRatio || 1, 2)

    // Брендовый градиент фона (единственное исключение из токенов — по брифу).
    const CYAN = [34, 211, 238] // #22d3ee
    const BLUE = [59, 130, 246] // #3b82f6 (brand-500)

    // Цвет точек сетки берём из токена --color-faint (адаптация под тему).
    const readToken = (name, fallback) => {
      try {
        const raw = getComputedStyle(document.documentElement)
          .getPropertyValue(name)
          .trim()
        const parts = raw.split(/\s+/).map(Number)
        if (parts.length === 3 && parts.every((n) => !Number.isNaN(n))) return parts
      } catch (e) {
        /* noop */
      }
      return fallback
    }
    const dot = readToken('--color-faint', isDark ? [100, 116, 139] : [156, 163, 175])

    let width = 0
    let height = 0
    let raf = 0
    let running = true
    let t = 0

    const blobs = []
    const nodes = []
    let gridPath = null

    // scan-луч: диагональный проход, изредка
    let scanProgress = 1 // 1 = завершён / не идёт
    let scanDelay = 180 // кадров до первого прохода (~3s @60fps)

    const GRID = 48 // шаг сетки точек данных

    const rand = (a, b) => a + Math.random() * (b - a)

    function seed() {
      // Боке-пятна
      blobs.length = 0
      const blobCount = subtle ? 2 : 3
      for (let i = 0; i < blobCount; i++) {
        blobs.push({
          x: rand(0, width),
          y: rand(0, height * 0.75),
          r: subtle ? rand(160, 280) : rand(220, 380),
          vx: rand(-0.12, 0.12),
          vy: rand(-0.09, 0.09),
          color: i % 2 === 0 ? CYAN : BLUE,
          alpha: subtle ? rand(0.04, 0.07) : rand(0.08, 0.14),
        })
      }

      // Пульсирующие «активные» узлы данных (только на лендинге)
      nodes.length = 0
      const nodeCount = subtle ? 0 : 6
      for (let i = 0; i < nodeCount; i++) {
        nodes.push({
          x: rand(0, width),
          y: rand(0, height),
          phase: rand(0, Math.PI * 2),
          speed: rand(0.6, 1.4),
          color: i % 2 === 0 ? CYAN : BLUE,
        })
      }

      // Статичная сетка точек — один Path2D, заливается одним вызовом за кадр.
      gridPath = null
      if (!subtle && typeof Path2D === 'function') {
        const p = new Path2D()
        for (let x = GRID / 2; x < width; x += GRID) {
          for (let y = GRID / 2; y < height; y += GRID) {
            p.moveTo(x + 1, y)
            p.arc(x, y, 1, 0, Math.PI * 2)
          }
        }
        gridPath = p
      }
    }

    function resize() {
      width = canvas.clientWidth || window.innerWidth
      height = canvas.clientHeight || window.innerHeight
      canvas.width = Math.floor(width * dpr)
      canvas.height = Math.floor(height * dpr)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      seed()
    }

    function drawStatic() {
      ctx.clearRect(0, 0, width, height)
      const g = ctx.createRadialGradient(
        width * 0.5,
        height * 0.32,
        0,
        width * 0.5,
        height * 0.32,
        Math.max(width, height) * 0.6,
      )
      g.addColorStop(0, `rgba(${BLUE[0]},${BLUE[1]},${BLUE[2]},${subtle ? 0.05 : 0.1})`)
      g.addColorStop(1, `rgba(${BLUE[0]},${BLUE[1]},${BLUE[2]},0)`)
      ctx.fillStyle = g
      ctx.fillRect(0, 0, width, height)
    }

    function drawScan() {
      if (subtle) return
      if (scanProgress >= 1) {
        scanDelay -= 1
        if (scanDelay <= 0) {
          scanProgress = 0
          scanDelay = Math.floor(rand(360, 720)) // 6–12s между проходами
        }
        return
      }
      scanProgress += 0.006
      const p = Math.min(scanProgress, 1)
      const span = width + height
      const pos = -height + p * span // диагональный сдвиг полосы
      const fade = Math.sin(p * Math.PI) // плавное появление/исчезание
      const g = ctx.createLinearGradient(pos - 140, 0, pos + 140, height)
      g.addColorStop(0, `rgba(${CYAN[0]},${CYAN[1]},${CYAN[2]},0)`)
      g.addColorStop(0.5, `rgba(${CYAN[0]},${CYAN[1]},${CYAN[2]},${0.1 * fade})`)
      g.addColorStop(1, `rgba(${BLUE[0]},${BLUE[1]},${BLUE[2]},0)`)
      ctx.fillStyle = g
      ctx.fillRect(0, 0, width, height)
    }

    function frame() {
      if (!running) return
      t += 1
      ctx.clearRect(0, 0, width, height)

      // 1) сетка точек данных (статичный Path2D)
      if (gridPath) {
        ctx.fillStyle = `rgba(${dot[0]},${dot[1]},${dot[2]},0.10)`
        ctx.fill(gridPath)
      }

      // 2) боке-пятна
      for (const b of blobs) {
        b.x += b.vx
        b.y += b.vy
        if (b.x < -b.r) b.x = width + b.r
        else if (b.x > width + b.r) b.x = -b.r
        if (b.y < -b.r) b.y = height + b.r
        else if (b.y > height + b.r) b.y = -b.r
        const g = ctx.createRadialGradient(b.x, b.y, 0, b.x, b.y, b.r)
        g.addColorStop(0, `rgba(${b.color[0]},${b.color[1]},${b.color[2]},${b.alpha})`)
        g.addColorStop(1, `rgba(${b.color[0]},${b.color[1]},${b.color[2]},0)`)
        ctx.fillStyle = g
        ctx.beginPath()
        ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2)
        ctx.fill()
      }

      // 3) пульсирующие узлы данных
      for (const n of nodes) {
        const a = 0.12 + 0.22 * (0.5 + 0.5 * Math.sin(t * 0.02 * n.speed + n.phase))
        ctx.fillStyle = `rgba(${n.color[0]},${n.color[1]},${n.color[2]},${a})`
        ctx.beginPath()
        ctx.arc(n.x, n.y, 1.8, 0, Math.PI * 2)
        ctx.fill()
      }

      // 4) scan-луч (дуга апертуры)
      drawScan()

      raf = requestAnimationFrame(frame)
    }

    function onResize() {
      resize()
      if (reduce) drawStatic()
    }

    function onVisibility() {
      if (document.hidden) {
        running = false
        if (raf) cancelAnimationFrame(raf)
      } else if (!reduce && !running) {
        running = true
        raf = requestAnimationFrame(frame)
      }
    }

    resize()
    window.addEventListener('resize', onResize)

    if (reduce) {
      // Статичный fallback — без rAF и подписки на видимость.
      drawStatic()
      return () => window.removeEventListener('resize', onResize)
    }

    document.addEventListener('visibilitychange', onVisibility)
    raf = requestAnimationFrame(frame)

    return () => {
      running = false
      if (raf) cancelAnimationFrame(raf)
      window.removeEventListener('resize', onResize)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [isDark, subtle])

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className={`pointer-events-none fixed inset-0 z-0 h-full w-full ${
        subtle ? 'opacity-70' : ''
      }`}
    />
  )
}
