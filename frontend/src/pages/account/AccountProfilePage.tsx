import { Lock, User, Bell } from 'lucide-react'

import { useEffect, useState, type ReactNode } from 'react'



import { fetchMe } from '../../lib/api/session'

import type { UserProfile } from '../../lib/api/types'

import { catalogApiUserMessage } from '../../lib/apiUserMessages'

import { usePageTitle } from '../../lib/page-title'

import { shouldSuppressInlineSessionSupersededMessage } from '../../lib/session-superseded-inline'



type ProfileState =

  | { status: 'loading' }

  | { status: 'superseded' }

  | { status: 'error'; message: string }

  | { status: 'ready'; profile: UserProfile }



function displayNameFromEmail(email: string): string {

  const local = email.split('@')[0]?.trim()

  return local || '—'

}



function AcctCardTitle({ icon: Icon, children }: { icon: typeof User; children: string }) {

  return (

    <h3 className="mb-5 flex items-center gap-2.5 text-[17px] font-extrabold tracking-tight text-rs-ink">

      <span className="flex size-[34px] shrink-0 items-center justify-center rounded-[10px] border border-[#e2ebff] bg-rs-sky-2 text-rs-blue">

        <Icon aria-hidden className="size-4" strokeWidth={2} />

      </span>

      {children}

    </h3>

  )

}



function AcctCard({ children }: { children: ReactNode }) {

  return (

    <div className="rounded-[22px] border border-rs-line bg-white p-7 shadow-rs-sm sm:px-[30px]">{children}</div>

  )

}



export default function AccountProfilePage() {

  usePageTitle('Account')

  const [state, setState] = useState<ProfileState>({ status: 'loading' })



  useEffect(() => {

    let cancelled = false

    async function load() {

      try {

        const profile = await fetchMe()

        if (!cancelled) setState({ status: 'ready', profile })

      } catch (err) {

        if (cancelled) return

        if (shouldSuppressInlineSessionSupersededMessage(err)) {

          setState({ status: 'superseded' })

          return

        }

        setState({ status: 'error', message: catalogApiUserMessage(err) })

      }

    }

    void load()

    return () => {

      cancelled = true

    }

  }, [])



  return (

    <section aria-labelledby="account-profile-heading" className="space-y-6">

      <div>

        <h2 id="account-profile-heading" className="text-xl font-extrabold text-rs-ink">

          Profile

        </h2>

        <p className="mt-1 text-sm font-semibold text-rs-body">Your sign-in details from your account.</p>

      </div>



      {state.status === 'loading' ? (

        <p className="text-sm font-semibold text-rs-muted" role="status">

          Loading profile…

        </p>

      ) : null}



      {state.status === 'superseded' ? (

        <p className="text-sm font-semibold text-rs-muted" role="status">

          Sign in again using the message above to view your profile.

        </p>

      ) : null}



      {state.status === 'error' ? (

        <p

          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-800"

          role="alert"

        >

          {state.message}

        </p>

      ) : null}



      {state.status === 'ready' ? (

        <>

          <AcctCard>

            <AcctCardTitle icon={User}>Profile Information</AcctCardTitle>

            <dl className="divide-y divide-rs-line-2 rounded-xl border border-rs-line">

              <div className="flex flex-col gap-1 px-4 py-4 sm:flex-row sm:gap-4">

                <dt className="w-32 shrink-0 text-sm font-bold text-rs-muted">Name</dt>

                <dd className="text-sm font-semibold text-rs-ink">{displayNameFromEmail(state.profile.email)}</dd>

              </div>

              <div className="flex flex-col gap-1 px-4 py-4 sm:flex-row sm:gap-4">

                <dt className="w-32 shrink-0 text-sm font-bold text-rs-muted">Email</dt>

                <dd className="text-sm font-semibold text-rs-ink">{state.profile.email || '—'}</dd>

              </div>

            </dl>

            <p className="mt-4 text-[13px] font-semibold leading-snug text-rs-muted">

              Additional profile fields will be editable after email and password sign-in ships.

            </p>

          </AcctCard>



          <AcctCard>

            <AcctCardTitle icon={Lock}>Security</AcctCardTitle>

            <p className="text-sm font-semibold leading-relaxed text-rs-body">

              Password changes and two-factor authentication will be available when native email sign-in launches.

            </p>

            <p className="mt-3 text-[13px] font-bold text-rs-muted">Two-factor authentication: Disabled</p>

          </AcctCard>



          <AcctCard>

            <AcctCardTitle icon={Bell}>Notification Preferences</AcctCardTitle>

            <p className="text-[12.5px] font-semibold leading-relaxed text-rs-muted">

              Course announcements, quiz results, certificates, Research Team updates, and product updates will be

              configurable here. Preferences are not editable in this release.

            </p>

          </AcctCard>

        </>

      ) : null}

    </section>

  )

}

