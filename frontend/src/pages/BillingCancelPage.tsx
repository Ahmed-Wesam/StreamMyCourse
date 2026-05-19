import { Link } from 'react-router-dom'

import { billingCancelMessage } from '../lib/subscribeCopy'

export default function BillingCancelPage() {
  return (
    <div className="mx-auto max-w-lg px-6 py-16 text-center">
      <h1 className="text-2xl font-bold text-foreground">Checkout canceled</h1>
      <p className="mt-4 text-muted-foreground">{billingCancelMessage}</p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Link
          to="/courses"
          className="inline-flex min-h-11 items-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90"
        >
          Browse courses
        </Link>
      </div>
    </div>
  )
}
