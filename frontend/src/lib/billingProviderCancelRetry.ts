import { fetchAuthSession } from 'aws-amplify/auth'

/** Session flag prefix: retry billing-edge provider cancel after 502 provider_cancel_failed. */
const PROVIDER_CANCEL_RETRY_STORAGE_PREFIX = 'smc_billing_provider_cancel_retry'

export function providerCancelRetryStorageKey(userSub: string): string {
  return `${PROVIDER_CANCEL_RETRY_STORAGE_PREFIX}_${userSub.trim()}`
}

export async function readCognitoSubFromSession(): Promise<string | null> {
  try {
    const session = await fetchAuthSession()
    const payload = session?.tokens?.idToken?.payload as Record<string, unknown> | undefined
    const sub = payload?.sub
    if (typeof sub === 'string' && sub.trim()) {
      return sub.trim()
    }
    return null
  } catch {
    return null
  }
}

export function readProviderCancelRetryFlag(userSub: string | null): boolean {
  if (!userSub) {
    return false
  }
  try {
    return sessionStorage.getItem(providerCancelRetryStorageKey(userSub)) === '1'
  } catch {
    return false
  }
}

export function setProviderCancelRetryFlag(userSub: string | null): void {
  if (!userSub) {
    return
  }
  try {
    sessionStorage.setItem(providerCancelRetryStorageKey(userSub), '1')
  } catch {
    // ignore private browsing / disabled storage
  }
}

export function clearProviderCancelRetryFlag(userSub: string | null): void {
  if (!userSub) {
    return
  }
  try {
    sessionStorage.removeItem(providerCancelRetryStorageKey(userSub))
  } catch {
    // ignore
  }
}
