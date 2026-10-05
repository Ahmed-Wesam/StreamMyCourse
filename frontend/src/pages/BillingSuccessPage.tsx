import { Link } from 'react-router-dom'

import { billingSuccessMessage } from '../lib/purchaseCopy'
import { usePageTitle } from '../lib/page-title'
import './BillingReturnPage.css'

export default function BillingSuccessPage() {
  usePageTitle('Payment')

  return (
    <div className="pg-billing-return">
      <div className="wrap billing-return-inner">
        <h1>Payment received</h1>
        <p>{billingSuccessMessage}</p>
        <Link to="/courses" className="btn btn-primary">
          Browse courses
        </Link>
      </div>
    </div>
  )
}
