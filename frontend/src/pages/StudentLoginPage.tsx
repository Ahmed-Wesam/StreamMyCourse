import { useAuthenticator } from '../lib/auth-ui'
import { Navigate } from 'react-router-dom'

import { SignIn } from '../components/auth/SignIn'
import { isAuthConfigured } from '../lib/auth'
import { loginHero } from '../lib/marketing/loginCopy'
import { usePageTitle } from '../lib/page-title'
import { Check } from 'lucide-react'
import { Eyebrow } from '../components/ui/Eyebrow'

export default function StudentLoginPage() {
  usePageTitle('Sign in')
  const authConfigured = isAuthConfigured()
  const { authStatus } = useAuthenticator((ctx) => [ctx.authStatus])

  if (!authConfigured) {
    return (
      <div className="mx-auto max-w-lg p-8 text-center text-rs-body">
        Sign-in is not available: set Cognito <code className="rounded bg-rs-sky-2 px-1">VITE_*</code> variables for this
        SPA.
      </div>
    )
  }

  if (authStatus === 'authenticated') {
    return <Navigate to="/" replace />
  }

  return (
    <div
      className="min-h-[calc(100vh-4rem)] bg-white text-rs-ink"
      data-testid="student-page-login"
    >
      <section className="relative overflow-hidden bg-gradient-to-b from-rs-sky-2 to-white px-5 pb-[84px] pt-[68px] sm:px-7">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(720px_480px_at_85%_10%,rgba(58,134,255,.12),transparent_62%),radial-gradient(500px_360px_at_0%_40%,rgba(30,94,255,.06),transparent_60%)]"
        />
        <div className="relative mx-auto grid max-w-wrap items-start gap-10 nav:grid-cols-[1.1fr_.9fr] nav:gap-16">
          <div data-testid="login-hero-column" className="pt-3">
            <Eyebrow>{loginHero.eyebrow}</Eyebrow>
            <h1 className="mt-5 text-[clamp(40px,5.5vw,62px)] font-extrabold leading-[1.03] tracking-tight text-rs-ink">
              {loginHero.titleLine1}
              <br />
              <span className="bg-rs-grad-cta bg-clip-text text-transparent">{loginHero.titleHighlight}</span>
            </h1>
            <p className="mt-[18px] max-w-[480px] text-[17px] leading-relaxed text-rs-body">{loginHero.sub}</p>
            <ul className="mb-[30px] mt-[26px] flex list-none flex-col gap-[11px] p-0">
              {loginHero.trustItems.map((item) => (
                <li
                  key={item}
                  className="flex items-center gap-[11px] text-[15px] font-bold text-rs-navy"
                >
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-[7px] bg-rs-grad-cta text-white shadow-[0_6px_14px_-6px_rgba(30,94,255,.55)]">
                    <Check aria-hidden className="size-[13px]" strokeWidth={2.8} />
                  </span>
                  {item}
                </li>
              ))}
            </ul>
            <p className="text-[14.5px] font-semibold text-rs-body">
              {loginHero.noAccountPrompt}{' '}
              <a href="/register" className="font-bold text-rs-blue hover:underline">
                {loginHero.createAccountCta}
              </a>
            </p>
          </div>
          <SignIn embedded />
        </div>
      </section>
    </div>
  )
}
