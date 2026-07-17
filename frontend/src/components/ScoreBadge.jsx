import { scoreBadgeClass } from '../utils/scoreColor'

export default function ScoreBadge({ score }) {
  if (score == null) return <span className="text-faint text-sm">—</span>
  return <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${scoreBadgeClass(score)}`}>{Math.round(score)}</span>
}
