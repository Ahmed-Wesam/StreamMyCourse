/** Display JOD amounts from API `amountMinor` (fils; 1000 fils = 1 JOD). */
export function formatJodMinor(amountMinor: number): string {
  if (!Number.isFinite(amountMinor) || amountMinor < 0) return ''
  const major = amountMinor / 1000
  if (amountMinor % 1000 === 0) {
    return new Intl.NumberFormat('en-JO', {
      style: 'currency',
      currency: 'JOD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(major)
  }
  return new Intl.NumberFormat('en-JO', { style: 'currency', currency: 'JOD' }).format(major)
}
