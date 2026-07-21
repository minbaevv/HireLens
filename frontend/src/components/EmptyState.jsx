// Переиспользуемое пустое состояние: иконка + заголовок + описание + действие.

export default function EmptyState({ icon: Icon, title, description, actionLabel, onAction, children }) {
  return (
    <div className="card py-16 px-6 text-center flex flex-col items-center animate-fade-in">
      {Icon && (
        <div className="inline-flex p-4 rounded-2xl bg-surface-muted text-faint mb-4">
          <Icon className="w-8 h-8" />
        </div>
      )}
      <p className="text-content font-semibold">{title}</p>
      {description && <p className="text-muted text-sm mt-1.5 max-w-sm">{description}</p>}
      {actionLabel && onAction && (
        <button className="btn-primary mt-5" onClick={onAction}>{actionLabel}</button>
      )}
      {children}
    </div>
  )
}
