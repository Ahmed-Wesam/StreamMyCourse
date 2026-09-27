/** Edit-friendly USD dollars string from API `amountMinor` (cents). */
export function usdMinorToInputValue(amountMinor: number): string {
  if (!Number.isFinite(amountMinor) || amountMinor < 0) return ''
  return (amountMinor / 100).toFixed(2)
}

/** Parse a dollar amount from an instructor input field into API cents. */
export function parseUsdInputToMinor(input: string): number | null {
  const trimmed = input.trim()
  if (trimmed === '') return null
  const dollars = Number(trimmed)
  if (!Number.isFinite(dollars) || dollars <= 0) return null
  return Math.round(dollars * 100)
}
