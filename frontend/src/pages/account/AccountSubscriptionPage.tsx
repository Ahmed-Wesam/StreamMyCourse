import { useCallback, useEffect, useState } from 'react'
import { Button } from '../../components/ui/Button'

import { cancelSubscription, createCheckoutSession, getSubscription } from '../../lib/api/billing'
import {
  isAlreadyCanceledError,
  isNotSubscribedError,
  isProviderAgreementMissingError,
  isProviderCancelFailedError,
} from '../../lib/api/client'
import type { SubscriptionSummary } from '../../lib/api/types'
import {
  clearProviderCancelRetryFlag,
  readCognitoSubFromSession,
  readProviderCancelRetryFlag,
  setProviderCancelRetryFlag,
} from '../../lib/billingProviderCancelRetry'
import { catalogApiUserMessage } from '../../lib/apiUserMessages'
import { usePageTitle } from '../../lib/page-title'
import { shouldSuppressInlineSessionSupersededMessage } from '../../lib/session-superseded-inline'
import { subscribeCtaLabel, subscribeCtaLoadingLabel } from '../../lib/subscribeCopy'

type PageState =
  | { status: 'loading' }
  | { status: 'not_subscribed' }
  | { status: 'superseded' }
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
  usePageTitle('Subscription')
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
      if (shouldSuppressInlineSessionSupersededMessage(err)) {
        setState({ status: 'superseded' })
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
        if (shouldSuppressInlineSessionSupersededMessage(err)) {
          setState({ status: 'superseded' })
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
    <section aria-labelledby="account-subscription-heading" className="text-rs-ink">
      <h2 id="account-subscription-heading" className="text-xl font-extrabold text-rs-ink">
        Manage subscription
      </h2>
      <p className="mt-1 text-sm font-semibold text-rs-body">
        View status and cancel at period end before your access ends.
      </p>

      {showPastDue ? <PastDueBanner /> : null}

      {state.status === 'loading' ? (
        <p className="mt-6 text-sm font-semibold text-rs-muted" role="status">
          Loading subscription…
        </p>
      ) : null}

      {state.status === 'superseded' ? (
        <p className="mt-6 text-sm font-semibold text-rs-muted" role="status">
          Sign in again using the message above to manage your subscription.
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
    <div className="mt-6 space-y-6 rounded-[22px] border border-rs-line bg-white p-6 shadow-rs-sm">
      <div>
        <h3 className="text-sm font-bold text-rs-muted">Status</h3>
        <p className="mt-1 text-base font-extrabold text-rs-ink" data-testid="subscription-status">
          {formatStatusLabel(subscription)}
        </p>
        <p className="mt-1 text-sm font-semibold text-rs-body" data-testid="subscription-amount">
          {subscription.planLabel}
        </p>
        <p className="mt-1 text-sm font-semibold text-rs-body" data-testid="subscription-period-end">
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
  const [subscribing, setSubscribing] = useState(false)
  const [subscribeError, setSubscribeError] = useState<string | null>(null)

  async function onSubscribe() {
    setSubscribing(true)
    setSubscribeError(null)
    try {
      const { redirect_url } = await createCheckoutSession()
      window.location.href = redirect_url
    } catch (err) {
      setSubscribeError(catalogApiUserMessage(err, 'subscribe'))
    } finally {
      setSubscribing(false)
    }
  }

  return (
    <div
      className="mt-6 rounded-[22px] border border-rs-line bg-white p-6 shadow-rs-sm"
      data-testid="subscription-not-subscribed"
    >
      <h3 className="text-base font-extrabold text-rs-ink">No subscription yet</h3>
      <p className="mt-2 text-sm font-semibold text-rs-body">
        Subscribe to unlock every published course, or browse the catalog while you decide.
      </p>
      {subscribeError ? (
        <p
          className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
          role="alert"
        >
          {subscribeError}
        </p>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-3">
        <Button to="/courses" variant="ghost" size="sm">
          Browse courses
        </Button>
        <Button
          type="button"
          size="sm"
          arrow
          disabled={subscribing}
          onClick={() => void onSubscribe()}
          data-testid="subscription-subscribe-btn"
        >
          {subscribing ? subscribeCtaLoadingLabel : subscribeCtaLabel}
        </Button>
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
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onCancel}
          disabled={actionBusy !== null}
          data-testid="subscription-cancel-btn"
        >
          {actionBusy === 'cancel' ? 'Canceling…' : 'Cancel at period end'}
        </Button>
      ) : null}
      {showProviderCancelRetry ? (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onCancel}
          disabled={actionBusy !== null}
          className="border-amber-300 bg-amber-50 text-amber-950 hover:border-amber-400 hover:text-amber-950"
          data-testid="subscription-retry-provider-cancel-btn"
        >
          {actionBusy === 'cancel' ? 'Retrying…' : 'Retry stopping renewal'}
        </Button>
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
