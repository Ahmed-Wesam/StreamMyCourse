/** Pill colors for latest module quiz score (lesson player sidebar). */
export function quizScorePercentPillClass(percent: number): string {
  const base = 'rounded-full px-2 py-0.5 text-[11px] font-semibold'
  if (percent < 50) return `${base} bg-red-100 text-red-700 ring-1 ring-red-200/80`
  if (percent < 75) return `${base} bg-amber-100 text-amber-800 ring-1 ring-amber-200/80`
  return `${base} bg-emerald-100 text-emerald-700 ring-1 ring-emerald-200/80`
}

export function formatModuleQuizQuestionCount(servedCount: number): string {
  return servedCount === 1 ? '1 question' : `${servedCount} questions`
}
