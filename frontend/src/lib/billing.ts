import { ApiError, catalogGet } from './api'

export type MerchantSetupChecklist = {
  paytabsAccountCreated: boolean
  profileIdConfigured: boolean
  repeatBillingEnabled: boolean
  termsUrlSet: boolean
  ipnRegistered: boolean
  testChargeSucceeded: boolean
  payoutMarkedReady: boolean
}

export type MerchantStatusResponse = {
  provider: string
  providerProfileId: string | null
  payoutReady: boolean
  payoutReadyAt: string | null
  setupChecklist: MerchantSetupChecklist
}

export const PAYTABS_GOING_LIVE_URL =
  'https://support.paytabs.com/en/support/solutions/articles/60000712804-going-live-from-a-to-z-guideline'

export const PAYTABS_API_KEYS_URL =
  'https://support.paytabs.com/en/support/solutions/articles/60000709801-how-to-get-my-authentication-integration-api-keys-'

export async function getMerchantStatus(): Promise<MerchantStatusResponse> {
  return catalogGet<MerchantStatusResponse>('/billing/merchant/status')
}

/** User-facing copy for merchant status API failures. */
export function merchantStatusUserMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 403 || err.code === 'forbidden') {
      return 'Only the designated billing teacher can view payment setup.'
    }
    if (err.status === 503 && err.code === 'billing_unconfigured') {
      return 'Billing is not configured for this environment yet. Contact the platform operator.'
    }
    if (err.message.trim()) return err.message.trim()
  }
  if (err instanceof Error && err.message.trim()) return err.message.trim()
  return 'Payment setup status could not be loaded. Please try again.'
}
