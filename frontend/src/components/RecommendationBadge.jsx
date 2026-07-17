import { useT } from '../i18n'

const REC_KEYS = {
  hire: 'recommendation.hire',
  maybe: 'recommendation.maybe',
  reject: 'recommendation.reject',
}

const REC_CLASSES = {
  hire: 'badge-hire',
  maybe: 'badge-maybe',
  reject: 'badge-reject',
}

export default function RecommendationBadge({ value }) {
  const { t } = useT()
  if (!value) return <span className="text-faint text-sm">—</span>
  const cls = REC_CLASSES[value] ?? 'badge-status bg-surface-muted text-muted'
  const label = REC_KEYS[value] ? t(REC_KEYS[value]) : value
  return <span className={cls}>{label}</span>
}
