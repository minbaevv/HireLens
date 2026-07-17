// Централизованное форматирование дат/времени в таймзоне приложения.
// Задание: всё показываем по бишкекскому времени (Asia/Bishkek, UTC+6),
// независимо от таймзоны браузера HR.
export const APP_TIMEZONE = 'Asia/Bishkek'

const DEFAULT_LOCALE = 'ru-RU'

export function fmtDateTime(dateLike, locale = DEFAULT_LOCALE) {
  if (!dateLike) return '—'
  const d = dateLike instanceof Date ? dateLike : new Date(dateLike)
  if (isNaN(d)) return '—'
  return d.toLocaleString(locale, { timeZone: APP_TIMEZONE })
}

export function fmtDate(dateLike, locale = DEFAULT_LOCALE) {
  if (!dateLike) return '—'
  const d = dateLike instanceof Date ? dateLike : new Date(dateLike)
  if (isNaN(d)) return '—'
  return d.toLocaleDateString(locale, { timeZone: APP_TIMEZONE })
}

// Смещение таймзоны (в минутах) для конкретного момента времени.
function tzOffsetMinutes(date, tz) {
  const dtf = new Intl.DateTimeFormat('en-US', {
    timeZone: tz, hour12: false,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
  const p = dtf.formatToParts(date).reduce((a, x) => { a[x.type] = x.value; return a }, {})
  const hour = p.hour === '24' ? '00' : p.hour
  const asUTC = Date.UTC(+p.year, +p.month - 1, +p.day, +hour, +p.minute, +p.second)
  return (asUTC - date.getTime()) / 60000
}

// Date → "YYYY-MM-DDTHH:mm" по стенным часам Asia/Bishkek (для datetime-local).
export function toInputValue(dateLike) {
  const d = dateLike instanceof Date ? dateLike : new Date(dateLike)
  const dtf = new Intl.DateTimeFormat('en-CA', {
    timeZone: APP_TIMEZONE, hour12: false,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
  const p = dtf.formatToParts(d).reduce((a, x) => { a[x.type] = x.value; return a }, {})
  const hh = p.hour === '24' ? '00' : p.hour
  return `${p.year}-${p.month}-${p.day}T${hh}:${p.minute}`
}

// Значение datetime-local (стенные часы Бишкека) → корректный UTC ISO для бэкенда.
export function inputValueToISO(value) {
  if (!value) return null
  const [datePart, timePart] = value.split('T')
  const [y, mo, d] = datePart.split('-').map(Number)
  const [h, mi] = (timePart || '00:00').split(':').map(Number)
  const provisional = Date.UTC(y, mo - 1, d, h, mi)
  const off = tzOffsetMinutes(new Date(provisional), APP_TIMEZONE)
  return new Date(provisional - off * 60000).toISOString()
}
