/**
 * Best-effort wipe of browser auth artifacts (Amplify may also use IndexedDB).
 * Shared by header sign-out and session-superseded handling.
 */
export function clearClientAuthState(): void {
  try {
    localStorage.clear()
  } catch {
    /* ignore */
  }
  try {
    sessionStorage.clear()
  } catch {
    /* ignore */
  }

  try {
    const cookies = document.cookie ? document.cookie.split(';') : []
    for (const raw of cookies) {
      const eqPos = raw.indexOf('=')
      const name = (eqPos > -1 ? raw.slice(0, eqPos) : raw).trim()
      if (!name) continue
      document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`
    }
  } catch {
    /* ignore */
  }
}
