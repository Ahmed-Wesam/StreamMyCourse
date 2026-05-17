import { useEffect, useState } from 'react'

/**
 * Subscribes to a CSS media query. When `matchMedia` is unavailable (e.g. some test
 * environments), returns `fallback` so callers can pick a safe default layout.
 */
export function useMediaQuery(query: string, fallback = false): boolean {
  const [matches, setMatches] = useState(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return fallback
    }
    return window.matchMedia(query).matches
  })

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return
    }
    const mql = window.matchMedia(query)
    const onChange = () => setMatches(mql.matches)
    onChange()
    mql.addEventListener('change', onChange)
    return () => mql.removeEventListener('change', onChange)
  }, [query])

  return matches
}

const MD_UP_QUERY = '(min-width: 768px)'

/** Synchronous `md` match for initial React state (avoids layout flash before effects run). */
export function readMdUpMatch(fallback = true): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return fallback
  }
  return window.matchMedia(MD_UP_QUERY).matches
}

/** Tailwind `md` — desktop lesson player chrome. */
export function useIsMdUp(fallback = true): boolean {
  return useMediaQuery(MD_UP_QUERY, fallback)
}
