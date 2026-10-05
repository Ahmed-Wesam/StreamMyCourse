import { Link } from 'react-router-dom'

import { billingCancelMessage } from '../lib/purchaseCopy'
import { usePageTitle } from '../lib/page-title'
import './BillingReturnPage.css'

export default function BillingCancelPage() {
  usePageTitle('Payment')

  return (
    <div className="pg-billing-return">
      <div className="wrap billing-return-inner">
        <h1>Checkout canceled</h1>
        <p>{billingCancelMessage}</p>
        <Link to="/courses" className="btn btn-primary">
          Browse courses
        </Link>
      </div>
    </div>
  )
}
