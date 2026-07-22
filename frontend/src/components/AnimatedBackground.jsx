// Фирменный анимированный фон HireLens — плавающие "аврора"-пятна + едва заметная точечная сетка.
// Рендерится как fixed-слой позади контента (z-index: 0), сам контент должен иметь relative + z-10.
// variant:
//   'landing' — самый яркий вариант для главной страницы
//   'auth'    — яркий вариант для экранов входа/регистрации/приглашений
//   'app'     — приглушённый вариант для рабочего интерфейса (не мешает читать таблицы/карточки)
export default function AnimatedBackground({ variant = 'app' }) {
  const subtle = variant === 'app'
  const blobClass = (name) => `aurora-blob ${name}${subtle ? ' aurora-blob-subtle' : ''}`

  return (
    <div className="bg-aurora" aria-hidden="true">
      <div className={blobClass('aurora-blob-a')} />
      <div className={blobClass('aurora-blob-b')} />
      <div className={blobClass('aurora-blob-c')} />
      <div className="aurora-grid" />
    </div>
  )
}
