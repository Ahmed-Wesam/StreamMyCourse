import { useEffect, useState } from 'react'

import { fetchMe, type UserProfile } from '../../lib/api'
import { catalogApiUserMessage } from '../../lib/apiUserMessages'

type ProfileState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; profile: UserProfile }

function displayNameFromEmail(email: string): string {
  const local = email.split('@')[0]?.trim()
  return local || '—'
}

export default function AccountProfilePage() {
  const [state, setState] = useState<ProfileState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const profile = await fetchMe()
        if (!cancelled) setState({ status: 'ready', profile })
      } catch (err) {
        if (!cancelled) setState({ status: 'error', message: catalogApiUserMessage(err) })
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <section aria-labelledby="account-profile-heading">
      <h2 id="account-profile-heading" className="text-xl font-semibold text-gray-900">
        Profile
      </h2>
      <p className="mt-1 text-sm text-gray-600">Your sign-in details from your account.</p>

      {state.status === 'loading' ? (
        <p className="mt-6 text-sm text-gray-500" role="status">
          Loading profile…
        </p>
      ) : null}

      {state.status === 'error' ? (
        <p className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
          {state.message}
        </p>
      ) : null}

      {state.status === 'ready' ? (
        <dl className="mt-6 divide-y divide-gray-200 rounded-xl border border-gray-200 bg-white">
          <div className="flex flex-col gap-1 px-4 py-4 sm:flex-row sm:gap-4">
            <dt className="w-32 shrink-0 text-sm font-medium text-gray-500">Name</dt>
            <dd className="text-sm text-gray-900">{displayNameFromEmail(state.profile.email)}</dd>
          </div>
          <div className="flex flex-col gap-1 px-4 py-4 sm:flex-row sm:gap-4">
            <dt className="w-32 shrink-0 text-sm font-medium text-gray-500">Email</dt>
            <dd className="text-sm text-gray-900">{state.profile.email || '—'}</dd>
          </div>
        </dl>
      ) : null}
    </section>
  )
}
