// Skeleton-загрузки: дают ощущение скорости вместо пустого спиннера.
// Используют встроенный Tailwind animate-pulse + семантические токены темы.

export function Skeleton({ className = '' }) {
  return <div className={`animate-pulse rounded-md bg-surface-muted ${className}`} />
}

// Список карточек (Jobs и подобные)
export function SkeletonList({ rows = 4 }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="card p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 space-y-3">
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-3 w-2/3" />
              <Skeleton className="h-3 w-1/4" />
            </div>
            <Skeleton className="h-8 w-20" />
          </div>
        </div>
      ))}
    </div>
  )
}

// Сетка карточек-статистики (Dashboard)
export function SkeletonStats({ count = 4 }) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card p-5 space-y-3">
          <Skeleton className="h-10 w-10 rounded-xl" />
          <Skeleton className="h-6 w-1/2" />
          <Skeleton className="h-3 w-3/4" />
        </div>
      ))}
    </div>
  )
}

// Строки таблицы (Candidates)
export function SkeletonRows({ rows = 6 }) {
  return (
    <div className="card overflow-hidden divide-y divide-line">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 px-6 py-4">
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3.5 w-1/4" />
            <Skeleton className="h-3 w-1/3" />
          </div>
          <Skeleton className="h-6 w-16" />
          <Skeleton className="h-6 w-10" />
          <Skeleton className="h-6 w-24" />
        </div>
      ))}
    </div>
  )
}

export default Skeleton
