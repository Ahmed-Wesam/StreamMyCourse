import { httpGet, httpPost } from './client'
import type {
  BundleOffer,
  CheckoutSessionResponse,
  CheckoutStatusResponse,
  CreateCheckoutSessionBody,
  PurchaseRecord,
  PurchasesListResponse,
} from './types'

/** Public bundle list price (GET /billing/bundle). */
export async function getBundle(): Promise<BundleOffer> {
  return httpGet<BundleOffer>('/billing/bundle')
}

/** Signed-in student's purchase history. */
export async function getPurchases(): Promise<PurchaseRecord[]> {
  const body = await httpGet<PurchasesListResponse>('/billing/purchases')
  return body.purchases ?? []
}

/** Start HyperPay widget checkout for a course or bundle (amount from server). */
export async function createCheckoutSession(
  params: CreateCheckoutSessionBody,
): Promise<CheckoutSessionResponse> {
  const body: Record<string, unknown> = { productType: params.productType }
  if (params.courseId) {
    body.courseId = params.courseId
  }
  if (params.billing) {
    body.billing = params.billing
  }
  return httpPost<CheckoutSessionResponse>('/billing/checkout-session', body)
}

/** Poll HyperPay checkout result after shopper return (POST /billing/checkout-status). */
export async function getCheckoutStatus(checkoutId: string): Promise<CheckoutStatusResponse> {
  return httpPost<CheckoutStatusResponse>('/billing/checkout-status', { checkoutId })
}
