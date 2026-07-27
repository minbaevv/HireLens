import { useT } from '../i18n'

const STATUS_KEYS = {
  applied: 'status.applied',
  interviewing: 'status.interviewing',
  completed: 'status.completed',
  invited: 'status.invited',
  hired: 'status.hired',
  rejected: 'status.rejected',
}

const STATUS_CLASSES = {
  applied: 'bg-blue-100 text-blue-800 dark:bg-blue-500/15 dark:text-blue-300',
  interviewing: 'bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300',
  completed: 'bg-surface-muted text-muted',
  invited: 'bg-purple-100 text-purple-800 dark:bg-purple-500/15 dark:text-purple-300',
  hired: 'bg-green-100 text-green-800 dark:bg-green-500/15 dark:text-green-300',
  rejected: 'bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-300',
}

export default function StatusBadge({ status }) {
  const { t } = useT()
  const cls = STATUS_CLASSES[status] ?? 'bg-surface-muted text-muted'
  const label = STATUS_KEYS[status] ? t(STATUS_KEYS[status]) : status
  return <span className={`badge-status ${cls}`}>{label}</span>
}
