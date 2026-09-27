import { httpGet, httpPost } from './client'
import type {
  BundleOffer,
  CheckoutSessionResponse,
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

/** Start PayTabs hosted checkout for a course or bundle (amount from server). */
export async function createCheckoutSession(
  params: CreateCheckoutSessionBody,
): Promise<CheckoutSessionResponse> {
  const body: Record<string, string> = { productType: params.productType }
  if (params.courseId) {
    body.courseId = params.courseId
  }
  return httpPost<CheckoutSessionResponse>('/billing/checkout-session', body)
}
