import { Link } from 'react-router-dom'

import { usePageTitle } from '../lib/page-title'

/** Checkout is offline while payments are rebuilt. No provider errors are shown. */
export default function CheckoutPage() {
  usePageTitle('Checkout')
  return (
    <div className="pg-checkout" data-testid="checkout-page">
      <div className="wrap" style={{ maxWidth: 640, margin: '48px auto', padding: '0 24px' }}>
        <h1>Checkout is closed</h1>
        <p>Course enrollment is not open yet. You can keep browsing the catalog.</p>
        <p>
          <Link to="/courses">Back to courses</Link>
        </p>
      </div>
    </div>
  )
}
