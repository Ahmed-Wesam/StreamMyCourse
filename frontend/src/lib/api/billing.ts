import { httpGet, httpPost } from './client'
import type {
  CancelSubscriptionResponse,
  CheckoutSessionResponse,
  SubscriptionSummary,
} from './types'

/** Load the signed-in student's manageable subscription summary. */
export async function getSubscription(): Promise<SubscriptionSummary> {
  return httpGet<SubscriptionSummary>('/billing/subscription')
}

/** Cancel subscription at period end (billing edge). */
export async function cancelSubscription(): Promise<CancelSubscriptionResponse> {
  return httpPost<CancelSubscriptionResponse>('/billing/cancel-subscription', {})
}

/** Start PayTabs hosted checkout for platform subscription (amount from server plan row). */
export async function createCheckoutSession(planId?: string): Promise<CheckoutSessionResponse> {
  const body = planId ? { planId } : {}
  return httpPost<CheckoutSessionResponse>('/billing/checkout-session', body)
}
