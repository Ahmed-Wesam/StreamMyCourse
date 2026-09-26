import { useEffect } from 'react'

import { BRAND_NAME } from './brand'

/** Sets `document.title` to `{title} — {BRAND_NAME}` or just `BRAND_NAME`. */
export function usePageTitle(title?: string): void {
  useEffect(() => {
    const trimmed = title?.trim()
    document.title = trimmed ? `${trimmed} — ${BRAND_NAME}` : BRAND_NAME
  }, [title])
}
