import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  cancelSubscription,
  getSubscription,
  isAlreadyCanceledError,
  isNotSubscribedError,
  isProviderAgreementMissingError,
  isProviderCancelFailedError,
  type SubscriptionSummary,
} from '../../lib/api'
import {
  clearProviderCancelRetryFlag,
  readCognitoSubFromSession,
  readProviderCancelRetryFlag,
  setProviderCancelRetryFlag,
} from '../../lib/billingProviderCancelRetry'
import { catalogApiUserMessage } from '../../lib/apiUserMessages'
import { subscribeCtaLabel } from '../../lib/subscribeCopy'

type PageState =
  | { status: 'loading' }
  | { status: 'not_subscribed' }
  | { status: 'error'; message: string }
  | { status: 'ready'; subscription: SubscriptionSummary }

function formatStatusLabel(summary: SubscriptionSummary): string {
  if (summary.status === 'past_due') return 'Past due'
  if (summary.status === 'canceled') {
    return summary.cancelAtPeriodEnd ? 'Canceled — access until period end' : 'Canceled'
  }
  if (summary.cancelAtPeriodEnd) return 'Active — cancels at period end'
  return 'Active'
}

function formatUtcDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
}

function renewalLine(summary: SubscriptionSummary): string {
  if (summary.nextBillingDate) {
    return `Next billing date: ${formatUtcDate(summary.nextBillingDate)}`
  }
  return `Current period ends: ${formatUtcDate(summary.currentPeriodEnd)}`
}

function isCanceledAtPeriodEnd(summary: SubscriptionSummary): boolean {
  return summary.status === 'canceled' && summary.cancelAtPeriodEnd
}

export default function AccountSubscriptionPage() {
  const [state, setState] = useState<PageState>({ status: 'loading' })
  const [actionBusy, setActionBusy] = useState<'cancel' | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [userSub, setUserSub] = useState<string | null>(null)
  const [providerCancelRetryNeeded, setProviderCancelRetryNeeded] = useState(false)

  useEffect(() => {
    let cancelled = false
    void readCognitoSubFromSession().then((sub) => {
      if (cancelled) return
      setUserSub(sub)
      setProviderCancelRetryNeeded(readProviderCancelRetryFlag(sub))
    })
    return () => {
      cancelled = true
    }
  }, [])

  const syncSubscription = useCallback(async () => {
    try {
      const subscription = await getSubscription()
      setState({ status: 'ready', subscription })
    } catch (err) {
      if (isNotSubscribedError(err)) {
        setState({ status: 'not_subscribed' })
        return
      }
      setState({ status: 'error', message: catalogApiUserMessage(err, 'loadSubscription') })
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    async function load() {
      setState({ status: 'loading' })
      try {
        const subscription = await getSubscription()
        if (!cancelled) setState({ status: 'ready', subscription })
      } catch (err) {
        if (cancelled) return
        if (isNotSubscribedError(err)) {
          setState({ status: 'not_subscribed' })
          return
        }
        setState({ status: 'error', message: catalogApiUserMessage(err, 'loadSubscription') })
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

  const resolveUserSub = useCallback(async (): Promise<string | null> => {
    if (userSub) {
      return userSub
    }
    const sub = await readCognitoSubFromSession()
    if (sub) {
      setUserSub(sub)
    }
    return sub
  }, [userSub])

  async function onCancel() {
    setActionBusy('cancel')
    const sub = await resolveUserSub()
    try {
      await cancelSubscription()
      clearProviderCancelRetryFlag(sub)
      setProviderCancelRetryNeeded(false)
      setActionError(null)
      await syncSubscription()
    } catch (err) {
      setActionError(catalogApiUserMessage(err, 'cancelSubscription'))
      if (isProviderCancelFailedError(err)) {
        setProviderCancelRetryFlag(sub)
        setProviderCancelRetryNeeded(true)
      } else if (isProviderAgreementMissingError(err) || isAlreadyCanceledError(err)) {
        clearProviderCancelRetryFlag(sub)
        setProviderCancelRetryNeeded(false)
      }
      await syncSubscription()
    } finally {
      setActionBusy(null)
    }
  }

  const subscription = state.status === 'ready' ? state.subscription : null
  const showPastDue = subscription?.pastDue === true
  const showProviderCancelRetry =
    subscription !== null &&
    isCanceledAtPeriodEnd(subscription) &&
    providerCancelRetryNeeded

  return (
    <section aria-labelledby="account-subscription-heading">
      <h2 id="account-subscription-heading" className="text-xl font-semibold text-gray-900">
        Manage subscription
      </h2>
      <p className="mt-1 text-sm text-gray-600">
        View status and cancel at period end before your access ends.
      </p>

      {showPastDue ? <PastDueBanner /> : null}

      {state.status === 'loading' ? (
        <p className="mt-6 text-sm text-gray-500" role="status">
          Loading subscription…
        </p>
      ) : null}

      {state.status === 'error' ? (
        <p className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
          {state.message}
        </p>
      ) : null}

      {state.status === 'not_subscribed' ? <NotSubscribedCard /> : null}

      {actionError ? (
        <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
          {actionError}
        </p>
      ) : null}

      {subscription ? (
        <SubscriptionSummaryCard
          subscription={subscription}
          actionBusy={actionBusy}
          showProviderCancelRetry={showProviderCancelRetry}
          onCancel={() => void onCancel()}
        />
      ) : null}
    </section>
  )
}

function SubscriptionSummaryCard(props: {
  subscription: SubscriptionSummary
  actionBusy: 'cancel' | null
  showProviderCancelRetry: boolean
  onCancel: () => void
}) {
  const { subscription, actionBusy, showProviderCancelRetry, onCancel } = props
  return (
    <div className="mt-6 space-y-6 rounded-xl border border-gray-200 bg-white p-6">
      <div>
        <h3 className="text-sm font-medium text-gray-500">Status</h3>
        <p className="mt-1 text-base font-semibold text-gray-900" data-testid="subscription-status">
          {formatStatusLabel(subscription)}
        </p>
        <p className="mt-1 text-sm text-gray-600" data-testid="subscription-amount">
          {subscription.planLabel}
        </p>
        <p className="mt-1 text-sm text-gray-600" data-testid="subscription-period-end">
          {renewalLine(subscription)}
        </p>
      </div>

      <SubscriptionActions
        subscription={subscription}
        actionBusy={actionBusy}
        showProviderCancelRetry={showProviderCancelRetry}
        onCancel={onCancel}
      />
    </div>
  )
}

function NotSubscribedCard() {
  return (
    <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6" data-testid="subscription-not-subscribed">
      <h3 className="text-base font-semibold text-gray-900">No subscription yet</h3>
      <p className="mt-2 text-sm text-gray-600">
        Subscribe to unlock every published course, or browse the catalog while you decide.
      </p>
      <div className="mt-4 flex flex-wrap gap-3">
        <Link
          to="/courses"
          className="inline-flex rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-800 hover:bg-gray-50"
        >
          Browse courses
        </Link>
        <Link
          to="/details#pricing"
          className="inline-flex rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
        >
          {subscribeCtaLabel}
        </Link>
      </div>
      </div>
  )
}

function SubscriptionActions({
  subscription,
  actionBusy,
  showProviderCancelRetry,
  onCancel,
}: {
  subscription: SubscriptionSummary
  actionBusy: 'cancel' | null
  showProviderCancelRetry: boolean
  onCancel: () => void
}) {
  return (
    <div className="flex flex-wrap gap-3">
      {subscription.canCancel ? (
        <button
          type="button"
          onClick={onCancel}
          disabled={actionBusy !== null}
          className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-800 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60"
          data-testid="subscription-cancel-btn"
        >
          {actionBusy === 'cancel' ? 'Canceling…' : 'Cancel at period end'}
        </button>
      ) : null}
      {showProviderCancelRetry ? (
        <button
          type="button"
          onClick={onCancel}
          disabled={actionBusy !== null}
          className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-950 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60"
          data-testid="subscription-retry-provider-cancel-btn"
        >
          {actionBusy === 'cancel' ? 'Retrying…' : 'Retry stopping renewal'}
        </button>
      ) : null}
    </div>
  )
}

function PastDueBanner() {
  return (
    <div
      className="mt-6 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900"
      role="alert"
      data-testid="subscription-past-due-banner"
    >
      Your last payment did not go through. Update your payment method in PayTabs to keep access.
    </div>
  )
}
