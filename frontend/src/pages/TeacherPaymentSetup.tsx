import { useCallback, useEffect, useState } from 'react'

import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Field } from '../components/ui/Field'
import { getBundle } from '../lib/api/billing'
import { setBundlePrice } from '../lib/api/pricing'
import { ApiError } from '../lib/api/client'
import {
  getMerchantStatus,
  merchantStatusUserMessage,
  PAYTABS_API_KEYS_URL,
  PAYTABS_GOING_LIVE_URL,
  type MerchantSetupChecklist,
  type MerchantStatusResponse,
} from '../lib/billing'
import { BRAND_NAME } from '../lib/brand'
import { privacyUrl, termsUrl } from '../lib/legalUrls'
import { usePageTitle } from '../lib/page-title'
import { parseUsdInputToMinor, usdMinorToInputValue } from '../lib/usdPriceInput'

type SetupChecklistKey = Exclude<keyof MerchantSetupChecklist, 'repeatBillingEnabled'>

const CHECKLIST_ORDER: SetupChecklistKey[] = [
  'paytabsAccountCreated',
  'profileIdConfigured',
  'termsUrlSet',
  'ipnRegistered',
  'testChargeSucceeded',
  'payoutMarkedReady',
]

const CHECKLIST_LABELS: Record<SetupChecklistKey, string> = {
  paytabsAccountCreated: 'PayTabs merchant account created',
  profileIdConfigured: 'Profile ID configured on the platform',
  termsUrlSet: 'Terms and conditions URL set in PayTabs',
  ipnRegistered: 'IPN webhook registered for this environment',
  testChargeSucceeded: 'Test charge succeeded',
  payoutMarkedReady: 'Payout marked ready',
}

function bundlePriceUserMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 403 || err.code === 'forbidden') {
      return 'Only the designated billing teacher can change the bundle price.'
    }
    if (err.code === 'invalid_amount') {
      return 'Enter a positive USD amount (for example 120.00).'
    }
    if (err.message.trim()) return err.message.trim()
  }
  if (err instanceof Error && err.message.trim()) return err.message.trim()
  return 'The bundle price could not be saved. Please try again.'
}


export default function TeacherPaymentSetup() {

  usePageTitle('Payments')

  const [status, setStatus] = useState<MerchantStatusResponse | null>(null)

  const [loading, setLoading] = useState(true)

  const [refreshing, setRefreshing] = useState(false)

  const [error, setError] = useState<string | null>(null)
  const [bundlePriceUsd, setBundlePriceUsd] = useState('')
  const [bundleLoading, setBundleLoading] = useState(true)
  const [bundleSaving, setBundleSaving] = useState(false)
  const [bundleError, setBundleError] = useState<string | null>(null)

  const loadBundleOffer = useCallback(async () => {
    try {
      setBundleLoading(true)
      setBundleError(null)
      const offer = await getBundle()
      setBundlePriceUsd(usdMinorToInputValue(offer.amountMinor))
    } catch (err) {
      setBundlePriceUsd('')
      setBundleError(
        err instanceof ApiError && err.code === 'bundle_not_configured'
          ? 'Bundle pricing is not configured yet. Contact the platform operator.'
          : bundlePriceUserMessage(err),
      )
    } finally {
      setBundleLoading(false)
    }
  }, [])

  const loadStatus = useCallback(async (isRefresh = false) => {
    try {

      if (isRefresh) {

        setRefreshing(true)

      } else {

        setLoading(true)

      }

      setError(null)

      const data = await getMerchantStatus()

      setStatus(data)

    } catch (err) {

      setStatus(null)

      setError(merchantStatusUserMessage(err))

    } finally {

      setLoading(false)

      setRefreshing(false)

    }

  }, [])



  useEffect(() => {
    void loadStatus()
    void loadBundleOffer()
  }, [loadStatus, loadBundleOffer])

  const handleSaveBundlePrice = async () => {
    const amountMinor = parseUsdInputToMinor(bundlePriceUsd)
    if (amountMinor == null) {
      setBundleError('Enter a positive USD amount (for example 120.00).')
      return
    }

    setBundleSaving(true)
    setBundleError(null)
    try {
      const offer = await setBundlePrice(amountMinor)
      setBundlePriceUsd(usdMinorToInputValue(offer.amountMinor))
    } catch (err) {
      setBundleError(bundlePriceUserMessage(err))
    } finally {
      setBundleSaving(false)
    }
  }

  const payoutReady = status?.payoutReady === true


  return (

    <main className="mx-auto w-full max-w-3xl px-4 py-8 text-rs-ink sm:px-6 lg:px-8">

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">

        <div>

          <h1 className="text-2xl font-extrabold tracking-tight text-rs-navy">Payment setup</h1>

          <p className="mt-2 text-sm text-rs-body">
            Students buy individual courses or a one-time USD all-access bundle through PayTabs
            hosted checkout. You are the merchant of record with PayTabs; {BRAND_NAME} hosts the API
            and payment notifications only.
          </p>
        </div>

        <Button

          type="button"

          variant="ghost"

          size="sm"

          className="shrink-0"

          disabled={loading || refreshing}

          onClick={() => void loadStatus(true)}

        >

          {refreshing ? 'Refreshing…' : 'Refresh status'}

        </Button>

      </div>



      <Card className="mb-8 p-4">

        <h2 className="text-sm font-extrabold text-rs-navy">PayTabs resources</h2>

        <ul className="mt-2 space-y-1 text-sm">

          <li>

            <a

              href={PAYTABS_GOING_LIVE_URL}

              target="_blank"

              rel="noopener noreferrer"

              className="font-semibold text-rs-blue hover:underline"

            >

              Going live with PayTabs

            </a>

          </li>

          <li>

            <a

              href={PAYTABS_API_KEYS_URL}

              target="_blank"

              rel="noopener noreferrer"

              className="font-semibold text-rs-blue hover:underline"

            >

              How to get API keys

            </a>

          </li>

        </ul>

        <p className="mt-3 text-xs text-rs-muted">

          Server keys are configured by the platform operator only — do not paste secrets in this

          app.

        </p>

      </Card>



      <Card className="mb-8 p-4">

        <h2 className="text-sm font-extrabold text-rs-navy">PayTabs URLs</h2>

        <p className="mt-2 text-sm text-rs-body">

          Copy these into your PayTabs merchant profile (terms and privacy fields). The checklist

          item for terms URL stays manual until you confirm it in PayTabs.

        </p>

        <dl className="mt-3 space-y-3 text-sm">

          <div>

            <dt className="font-semibold text-rs-navy">Terms and conditions</dt>

            <dd className="mt-1 break-all font-mono text-xs text-rs-body">{termsUrl()}</dd>

          </div>

          <div>

            <dt className="font-semibold text-rs-navy">Privacy policy</dt>

            <dd className="mt-1 break-all font-mono text-xs text-rs-body">{privacyUrl()}</dd>

          </div>

        </dl>

      </Card>

      <Card className="mb-8 p-4">
        <h2 className="text-sm font-extrabold text-rs-navy">All-access bundle price</h2>
        <p className="mt-2 text-sm text-rs-body">
          Set the one-time USD price students pay for the full course catalog bundle.
        </p>
        {bundleLoading ? (
          <p className="mt-3 text-sm text-rs-body" role="status">
            Loading bundle price…
          </p>
        ) : (
          <>
            <Field
              label="Bundle price (USD)"
              type="text"
              inputMode="decimal"
              autoComplete="off"
              className="mt-3"
              value={bundlePriceUsd}
              error={bundleError ?? undefined}
              onChange={(e) => {
                setBundlePriceUsd(e.target.value)
                if (bundleError) setBundleError(null)
              }}
            />
            <Button
              type="button"
              size="sm"
              className="mt-1"
              disabled={bundleSaving}
              onClick={() => void handleSaveBundlePrice()}
            >
              {bundleSaving ? 'Saving…' : 'Save bundle price'}
            </Button>
          </>
        )}
      </Card>

      {loading && !status ? (
        <p className="text-sm text-rs-body" role="status">

          Loading payment setup…

        </p>

      ) : null}



      {error ? (

        <p

          className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"

          role="alert"

        >

          {error}

        </p>

      ) : null}



      {status ? (

        <section aria-labelledby="setup-checklist-heading">

          <div className="mb-4 flex flex-wrap items-center gap-2">

            <h2 id="setup-checklist-heading" className="text-lg font-extrabold text-rs-navy">

              Setup checklist

            </h2>

            <span data-testid="merchant-payout-status">

              <Badge tone={payoutReady ? 'success' : 'blue'}>

                {payoutReady ? 'Payout ready' : 'Setup in progress'}

              </Badge>

            </span>

          </div>

          {status.providerProfileId ? (

            <p className="mb-4 text-sm text-rs-body">

              Profile ID:{' '}

              <span className="font-mono font-semibold text-rs-navy">{status.providerProfileId}</span>

            </p>

          ) : null}

          <Card className="overflow-hidden p-0">

            <ul className="divide-y divide-rs-line">

              {CHECKLIST_ORDER.map((key) => {

                const done = status.setupChecklist[key]

                return (

                  <li

                    key={key}

                    data-testid={`checklist-${key}`}

                    className="flex items-center justify-between gap-4 px-4 py-3 text-sm"

                  >

                    <span className="text-rs-navy">{CHECKLIST_LABELS[key]}</span>

                    <Badge tone={done ? 'success' : 'blue'}>{done ? 'Complete' : 'Pending'}</Badge>

                  </li>

                )

              })}

            </ul>

          </Card>

          {status.payoutReadyAt ? (

            <p className="mt-3 text-xs text-rs-muted">

              Payout ready since {new Date(status.payoutReadyAt).toLocaleString()}

            </p>

          ) : null}

        </section>

      ) : null}

    </main>

  )

}

