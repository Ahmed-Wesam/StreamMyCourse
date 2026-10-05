const STORAGE_KEY = 'streammycourse.checkoutPendingPurchaseId'

export function setCheckoutPendingPurchaseId(purchaseId: string): void {
  const id = purchaseId.trim()
  if (!id) return
  try {
    sessionStorage.setItem(STORAGE_KEY, id)
  } catch {
    // sessionStorage may be unavailable in some embed contexts
  }
}

export function readCheckoutPendingPurchaseId(): string | null {
  try {
    const id = sessionStorage.getItem(STORAGE_KEY)?.trim()
    return id || null
  } catch {
    return null
  }
}

export function clearCheckoutPendingPurchaseId(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // ignore
  }
}
