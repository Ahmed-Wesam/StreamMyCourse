import { Button } from '../components/ui/Button'

import { billingSuccessMessage } from '../lib/purchaseCopy'

import { usePageTitle } from '../lib/page-title'



export default function BillingSuccessPage() {

  usePageTitle('Payment')

  return (

    <div className="min-h-[calc(100vh-4rem)] bg-white text-rs-ink">

      <div className="mx-auto max-w-lg px-6 py-16 text-center">

        <h1 className="text-2xl font-extrabold text-rs-ink">Payment received</h1>

        <p className="mt-4 text-[17px] leading-relaxed text-rs-body">{billingSuccessMessage}</p>

        <div className="mt-8 flex flex-wrap justify-center gap-3">

          <Button to="/courses" arrow>

            Browse courses

          </Button>

        </div>

      </div>

    </div>

  )

}

