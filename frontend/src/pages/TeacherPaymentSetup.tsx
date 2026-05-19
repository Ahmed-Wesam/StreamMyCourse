import { useCallback, useEffect, useState } from 'react'

import {
  getMerchantStatus,
  merchantStatusUserMessage,
  PAYTABS_API_KEYS_URL,
  PAYTABS_GOING_LIVE_URL,
  type MerchantSetupChecklist,
  type MerchantStatusResponse,
} from '../lib/billing'

const CHECKLIST_ORDER: (keyof MerchantSetupChecklist)[] = [
  'paytabsAccountCreated',
  'profileIdConfigured',
  'repeatBillingEnabled',
  'termsUrlSet',
  'ipnRegistered',
  'testChargeSucceeded',
  'payoutMarkedReady',
]

const CHECKLIST_LABELS: Record<keyof MerchantSetupChecklist, string> = {
  paytabsAccountCreated: 'PayTabs merchant account created',
  profileIdConfigured: 'Profile ID configured on the platform',
  repeatBillingEnabled: 'Repeat billing enabled in PayTabs',
  termsUrlSet: 'Terms and conditions URL set in PayTabs',
  ipnRegistered: 'IPN webhook registered for this environment',
  testChargeSucceeded: 'Test charge succeeded',
  payoutMarkedReady: 'Payout marked ready',
}

export default function TeacherPaymentSetup() {
  const [status, setStatus] = useState<MerchantStatusResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
  }, [loadStatus])

  const payoutReady = status?.payoutReady === true

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">Payment setup</h1>
          <p className="mt-2 text-sm text-gray-600">
            Student subscriptions are billed in Jordanian dinar (JOD) as a monthly all-access plan.
            You are the merchant of record with PayTabs; Stream My Course hosts the API and payment
            notifications only.
          </p>
        </div>
        <button
          type="button"
          className="inline-flex shrink-0 items-center justify-center rounded-md border border-emerald-600 bg-white px-4 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-50 disabled:opacity-60"
          disabled={loading || refreshing}
          onClick={() => void loadStatus(true)}
        >
          {refreshing ? 'Refreshing…' : 'Refresh status'}
        </button>
      </div>

      <section className="mb-8 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <h2 className="text-sm font-semibold text-gray-900">PayTabs resources</h2>
        <ul className="mt-2 space-y-1 text-sm">
          <li>
            <a
              href={PAYTABS_GOING_LIVE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-emerald-700 hover:text-emerald-800"
            >
              Going live with PayTabs
            </a>
          </li>
          <li>
            <a
              href={PAYTABS_API_KEYS_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-emerald-700 hover:text-emerald-800"
            >
              How to get API keys
            </a>
          </li>
        </ul>
        <p className="mt-3 text-xs text-gray-500">
          Server keys are configured by the platform operator only — do not paste secrets in this
          app.
        </p>
      </section>

      {loading && !status ? (
        <p className="text-sm text-gray-600" role="status">
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
            <h2 id="setup-checklist-heading" className="text-lg font-semibold text-gray-900">
              Setup checklist
            </h2>
            <span
              data-testid="merchant-payout-status"
              className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                payoutReady ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-900'
              }`}
            >
              {payoutReady ? 'Payout ready' : 'Setup in progress'}
            </span>
          </div>
          {status.providerProfileId ? (
            <p className="mb-4 text-sm text-gray-600">
              Profile ID:{' '}
              <span className="font-mono text-gray-800">{status.providerProfileId}</span>
            </p>
          ) : null}
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {CHECKLIST_ORDER.map((key) => {
              const done = status.setupChecklist[key]
              return (
                <li
                  key={key}
                  data-testid={`checklist-${key}`}
                  className="flex items-center justify-between gap-4 px-4 py-3 text-sm"
                >
                  <span className="text-gray-800">{CHECKLIST_LABELS[key]}</span>
                  <span
                    className={`shrink-0 font-medium ${done ? 'text-emerald-700' : 'text-amber-700'}`}
                  >
                    {done ? 'Complete' : 'Pending'}
                  </span>
                </li>
              )
            })}
          </ul>
          {status.payoutReadyAt ? (
            <p className="mt-3 text-xs text-gray-500">
              Payout ready since {new Date(status.payoutReadyAt).toLocaleString()}
            </p>
          ) : null}
        </section>
      ) : null}
    </main>
  )
}
