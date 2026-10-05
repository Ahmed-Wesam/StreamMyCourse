/** Edit-friendly whole JOD string from API fils (`amountMinor`). */
export function jodMinorToInputValue(amountMinor: number): string {
  if (!Number.isFinite(amountMinor) || amountMinor < 0) return ''
  if (amountMinor % 1000 !== 0) return ''
  return String(amountMinor / 1000)
}

/** Parse a whole-number JOD amount from an instructor input field into API fils. */
export function parseJodInputToMinor(input: string): number | null {
  const trimmed = input.trim()
  if (trimmed === '') return null
  if (!/^\d+$/.test(trimmed)) return null
  const major = Number(trimmed)
  if (!Number.isFinite(major) || major <= 0) return null
  return major * 1000
}
