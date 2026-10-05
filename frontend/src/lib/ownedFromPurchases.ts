import type { PurchaseRecord } from './api/types'

type OwnedCoursesScope = {
  ownsAllPublished: boolean
  courseIds: Set<string>
}

/** Derive owned course ids from paid purchase rows (RS-5). */
export function ownedCoursesFromPurchases(purchases: PurchaseRecord[]): OwnedCoursesScope {
  const courseIds = new Set<string>()
  let ownsAllPublished = false
  for (const row of purchases) {
    if (row.status !== 'paid') continue
    if (row.productType === 'bundle') {
      ownsAllPublished = true
      continue
    }
    if (row.productType === 'course' && row.courseId) {
      courseIds.add(row.courseId)
    }
  }
  return { ownsAllPublished, courseIds }
}
