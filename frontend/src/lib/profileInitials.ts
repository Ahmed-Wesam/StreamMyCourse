function emailLocalPart(email: string): string {
  const trimmed = email.trim()
  const at = trimmed.indexOf('@')
  return at > 0 ? trimmed.slice(0, at) : trimmed
}

/** Up to two initials for avatars (header, account hero, dashboard). */
export function profileInitials(input: {
  givenName?: string | null
  familyName?: string | null
  email?: string | null
  displayName?: string | null
}): string {
  const given = input.givenName?.trim()
  const family = input.familyName?.trim()
  const nameParts = [given, family].filter((part): part is string => Boolean(part))
  if (nameParts.length > 0) {
    return nameParts
      .slice(0, 2)
      .map((part) => part.charAt(0))
      .join('')
      .toUpperCase()
  }

  const email = input.email?.trim()
  if (email) {
    const local = emailLocalPart(email).replace(/[^a-zA-Z0-9]/g, '')
    if (local.length >= 2) return (local.charAt(0) + local.charAt(1)).toUpperCase()
    if (local.length === 1) return local.charAt(0).toUpperCase()
  }

  const display = input.displayName?.trim()
  if (display && !display.includes('@')) {
    const words = display.split(/\s+/).filter(Boolean)
    if (words.length >= 2) {
      return words
        .slice(0, 2)
        .map((word) => word.charAt(0))
        .join('')
        .toUpperCase()
    }
    if (words.length === 1 && words[0].length > 0) {
      return words[0].charAt(0).toUpperCase()
    }
  }

  return '?'
}
