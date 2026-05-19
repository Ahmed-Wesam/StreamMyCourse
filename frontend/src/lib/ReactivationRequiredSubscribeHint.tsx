import { Link } from 'react-router-dom'

import { reactivationRequiredAccountPath } from './apiUserMessages'

/** Shown when checkout returns 409 reactivation_required (canceled-in-period). */
export function ReactivationRequiredSubscribeHint() {
  return (
    <>
      You still have access until your billing period ends.{' '}
      <Link to={reactivationRequiredAccountPath} className="font-semibold underline">
        Manage subscription
      </Link>{' '}
      in your account to reactivate—no new charge today.
    </>
  )
}
