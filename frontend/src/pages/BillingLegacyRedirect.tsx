import { Navigate, useLocation } from 'react-router-dom'

/** Preserve query string when moving legacy PayTabs return paths to HyperPay result. */
export function BillingSuccessRedirect() {
  const { search } = useLocation()
  return <Navigate to={`/billing/result${search}`} replace />
}

export function BillingCancelRedirect() {
  const { search } = useLocation()
  const params = new URLSearchParams(search)
  if (!params.has('canceled')) {
    params.set('canceled', '1')
  }
  const next = params.toString()
  return <Navigate to={`/billing/result${next ? `?${next}` : ''}`} replace />
}
