/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it } from 'vitest'

import {
  clearCheckoutPendingPurchaseId,
  readCheckoutPendingContext,
  readCheckoutPendingPurchaseId,
  setCheckoutPendingContext,
  setCheckoutPendingPurchaseId,
} from './checkoutPendingPurchase'

describe('checkoutPendingPurchase', () => {
  afterEach(() => {
    clearCheckoutPendingPurchaseId()
  })

  it('stores and reads purchaseId', () => {
    setCheckoutPendingPurchaseId('p-1')
    expect(readCheckoutPendingPurchaseId()).toBe('p-1')
    clearCheckoutPendingPurchaseId()
    expect(readCheckoutPendingPurchaseId()).toBeNull()
  })

  it('stores productType and courseId in context', () => {
    setCheckoutPendingContext({
      purchaseId: 'p-2',
      productType: 'course',
      courseId: 'c-9',
    })
    expect(readCheckoutPendingContext()).toEqual({
      purchaseId: 'p-2',
      productType: 'course',
      courseId: 'c-9',
    })
  })
})
