/**
 * HireLens — фирменный логотип (circuit-профиль + галочка).
 *
 * Голова в профиль, собранная из дорожек печатной платы (circuit) с узелками —
 * метафора AI-анализа кандидата; поверх — крупная галочка «одобрено/подходит»
 * и дуга апертуры сверху. Cyan-градиент как на фирменном вордмарке.
 *
 * Презентационный компонент: размер задаётся через `className` (w-* h-*).
 * Цвета фиксированы фирменным градиентом (cyan→brand), поэтому mark читается
 * одинаково на светлом и тёмном фоне. Доступность — role="img" + <title>.
 * Cleanup не требуется (нет эффектов/подписок). `gradId` уникализирует id
 * градиента, чтобы несколько логотипов на странице не конфликтовали.
 */
export default function Logo({ className = 'w-8 h-8', title = 'HireLens', gradId = 'hl-grad' }) {
  const glowId = `${gradId}-glow`
  return (
    <svg
      viewBox="0 0 64 64"
      className={className}
      role="img"
      aria-label={title}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <title>{title}</title>
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#22d3ee" />
          <stop offset="1" stopColor="#3b82f6" />
        </linearGradient>
        <filter id={glowId} x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="1.1" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      <g stroke={`url(#${gradId})`} filter={`url(#${glowId})`}
         strokeLinecap="round" strokeLinejoin="round">
        {/* Дуга апертуры сверху-слева */}
        <path d="M10 30 A 22 22 0 0 1 30 10" fill="none" strokeWidth="2.4" />

        {/* Контур головы в профиль (лоб → нос → подбородок → шея) */}
        <path
          d="M40 15
             C 30 13, 21 20, 21 31
             C 21 37, 24 40, 24 44
             L 20 48
             L 26 50
             L 26 54"
          fill="none"
          strokeWidth="2.6"
        />

        {/* Circuit-дорожки внутри головы */}
        <g strokeWidth="1.8">
          <path d="M27 24 H 37" fill="none" />
          <path d="M31 31 H 42" fill="none" />
          <path d="M28 38 H 35" fill="none" />
          <path d="M37 24 V 31" fill="none" />
        </g>

        {/* Узелки схемы */}
        <g fill={`url(#${gradId})`} stroke="none">
          <circle cx="27" cy="24" r="1.7" />
          <circle cx="42" cy="31" r="1.7" />
          <circle cx="28" cy="38" r="1.7" />
          <circle cx="35" cy="38" r="1.5" />
        </g>
      </g>

      {/* Крупная галочка поверх — «одобрено/подходит» */}
      <path
        d="M24 34 L 32 43 L 52 18"
        stroke={`url(#${gradId})`}
        strokeWidth="5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
        filter={`url(#${glowId})`}
      />
    </svg>
  )
}
