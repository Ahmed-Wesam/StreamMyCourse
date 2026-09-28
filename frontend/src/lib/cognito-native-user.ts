type IdTokenPayload = Record<string, unknown>

function parseIdentities(payload: IdTokenPayload): unknown[] {
  const raw = payload.identities
  if (raw == null) return []
  if (Array.isArray(raw)) return raw
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw) as unknown
      return Array.isArray(parsed) ? parsed : []
    } catch {
      return []
    }
  }
  return []
}

/** True when the user signed up with email/password (not federated Google). */
export function isNativeCognitoPasswordUser(payload: IdTokenPayload | undefined): boolean {
  if (!payload) return false
  const identities = parseIdentities(payload)
  return identities.length === 0
}
