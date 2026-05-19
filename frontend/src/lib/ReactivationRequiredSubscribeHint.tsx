import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { isReactivationRequiredError } from './api'
import { catalogApiUserMessage } from './apiUserMessages'

const REACTIVATION_ACCOUNT_PATH = '/account/subscription'

/** Shown when checkout returns 409 reactivation_required (canceled-in-period). */
function ReactivationRequiredSubscribeHint() {
  return (
    <>
      You still have access until your billing period ends.{' '}
      <Link to={REACTIVATION_ACCOUNT_PATH} className="font-semibold underline">
        Manage subscription
      </Link>{' '}
      in your account to reactivate—no new charge today.
    </>
  )
}

/** Subscribe paywall error: rich hint for reactivation_required, else catalog message. */
export function formatSubscribeError(err: unknown): ReactNode {
  if (isReactivationRequiredError(err)) {
    return <ReactivationRequiredSubscribeHint />
  }
  return catalogApiUserMessage(err, 'subscribe')
}
