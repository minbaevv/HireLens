/**
 * Единый источник цветовой шкалы для числовых оценок (0–100).
 * Раньше пороговая раскраска дублировалась в ScoreBadge, DashboardPage
 * (последние кандидаты) и CandidatesPage (pre_score) с расхождением оттенков.
 *
 * @param {number} score - оценка 0–100.
 * @param {{ high?: number, mid?: number }} [thresholds] - границы зелёный/жёлтый.
 * @returns {string} Tailwind-классы фон+текст (со светлой и тёмной темой).
 */
export function scoreBadgeClass(score, { high = 75, mid = 50 } = {}) {
  if (score >= high) return 'bg-green-100 text-green-800 dark:bg-green-500/15 dark:text-green-300'
  if (score >= mid) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-500/15 dark:text-yellow-300'
  return 'bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-300'
}
