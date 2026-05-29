/** sessionStorage key — survives route change to /login so the supersede message stays visible. */
export const SESSION_SUPERSEDED_BANNER_KEY = 'smc:sessionSupersededMessage'

export function persistSessionSupersededBanner(message: string): void {
  try {
    sessionStorage.setItem(SESSION_SUPERSEDED_BANNER_KEY, message)
  } catch {
    /* ignore */
  }
}

export function readSessionSupersededBanner(): string | null {
  try {
    const raw = sessionStorage.getItem(SESSION_SUPERSEDED_BANNER_KEY)
    return raw?.trim() ? raw.trim() : null
  } catch {
    return null
  }
}

export function clearSessionSupersededBanner(): void {
  try {
    sessionStorage.removeItem(SESSION_SUPERSEDED_BANNER_KEY)
  } catch {
    /* ignore */
  }
}
