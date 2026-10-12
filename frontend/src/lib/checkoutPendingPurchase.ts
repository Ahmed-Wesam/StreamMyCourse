const PURCHASE_ID_KEY = 'streammycourse.checkoutPendingPurchaseId'
const CONTEXT_KEY = 'streammycourse.checkoutPendingContext'

export type CheckoutPendingContext = {
  purchaseId: string
  productType: 'course' | 'bundle'
  courseId?: string
}

function writeSession(key: string, value: string): void {
  try {
    sessionStorage.setItem(key, value)
  } catch {
    // sessionStorage may be unavailable
  }
}

function readSession(key: string): string | null {
  try {
    const value = sessionStorage.getItem(key)?.trim()
    return value || null
  } catch {
    return null
  }
}

function removeSession(key: string): void {
  try {
    sessionStorage.removeItem(key)
  } catch {
    // ignore
  }
}

export function setCheckoutPendingPurchaseId(purchaseId: string): void {
  const id = purchaseId.trim()
  if (!id) return
  writeSession(PURCHASE_ID_KEY, id)
}

export function readCheckoutPendingPurchaseId(): string | null {
  return readSession(PURCHASE_ID_KEY)
}

export function setCheckoutPendingContext(ctx: CheckoutPendingContext): void {
  const purchaseId = ctx.purchaseId.trim()
  if (!purchaseId) return
  writeSession(PURCHASE_ID_KEY, purchaseId)
  writeSession(
    CONTEXT_KEY,
    JSON.stringify({
      purchaseId,
      productType: ctx.productType,
      courseId: ctx.courseId?.trim() || undefined,
    }),
  )
}

export function readCheckoutPendingContext(): CheckoutPendingContext | null {
  const raw = readSession(CONTEXT_KEY)
  if (raw) {
    try {
      const parsed = JSON.parse(raw) as CheckoutPendingContext
      if (parsed.purchaseId && (parsed.productType === 'course' || parsed.productType === 'bundle')) {
        return parsed
      }
    } catch {
      // fall through to purchase id only
    }
  }
  const purchaseId = readCheckoutPendingPurchaseId()
  if (!purchaseId) return null
  return { purchaseId, productType: 'bundle' }
}

export function clearCheckoutPendingPurchaseId(): void {
  removeSession(PURCHASE_ID_KEY)
  removeSession(CONTEXT_KEY)
}
