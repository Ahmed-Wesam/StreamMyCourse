const AMPLIFY_STORAGE_KEY_MARKERS = ['CognitoIdentityServiceProvider', 'amplify', 'aws-amplify'] as const

function storageKeyLooksLikeAmplifyAuth(key: string): boolean {
  const lower = key.toLowerCase()
  return AMPLIFY_STORAGE_KEY_MARKERS.some((marker) => lower.includes(marker.toLowerCase()))
}

/** Remove Cognito / Amplify keys from localStorage (tokens also live in IndexedDB). */
function clearAmplifyLocalStorageKeys(): void {
  try {
    const keys: string[] = []
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && storageKeyLooksLikeAmplifyAuth(key)) keys.push(key)
    }
    for (const key of keys) {
      localStorage.removeItem(key)
    }
  } catch {
    /* ignore */
  }
}

/** Best-effort wipe of Amplify IndexedDB token caches (v6). */
async function clearAmplifyIndexedDbCaches(): Promise<void> {
  if (typeof indexedDB === 'undefined' || typeof indexedDB.databases !== 'function') return
  try {
    const databases = await indexedDB.databases()
    await Promise.all(
      databases.map((db) => {
        const name = db.name ?? ''
        if (!name || !storageKeyLooksLikeAmplifyAuth(name)) return Promise.resolve()
        return new Promise<void>((resolve) => {
          const req = indexedDB.deleteDatabase(name)
          req.onsuccess = () => resolve()
          req.onerror = () => resolve()
          req.onblocked = () => resolve()
        })
      }),
    )
  } catch {
    /* ignore */
  }
}

/** Drop Amplify/Cognito token caches without touching sessionStorage banner state. */
export function clearAmplifyAuthCaches(): void {
  clearAmplifyLocalStorageKeys()
  void clearAmplifyIndexedDbCaches()
}
