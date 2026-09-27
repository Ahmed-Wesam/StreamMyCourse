/** Display USD amounts from API `amountMinor` (cents). */
export function formatUsdMinor(amountMinor: number): string {
  if (!Number.isFinite(amountMinor) || amountMinor < 0) return ''
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amountMinor / 100)
}
