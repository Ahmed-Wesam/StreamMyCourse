import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'

import { ProfileMenu } from '../components/layout/ProfileMenu'
import { SiteHeader, type SiteNavLink } from '../components/layout/SiteHeader'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { fetchMe } from '../lib/api/session'
import { useAuthenticator } from '../lib/auth-ui'
import { useCognitoDisplayName } from '../lib/cognito-display-name'

const studentSiteUrl =
  typeof import.meta.env.VITE_STUDENT_SITE_URL === 'string' &&
  import.meta.env.VITE_STUDENT_SITE_URL.length > 0
    ? import.meta.env.VITE_STUDENT_SITE_URL
    : 'https://researchspectrum.org'

const TEACHER_NAV: SiteNavLink[] = [
  { href: '/', label: 'Dashboard' },
  { href: '/settings/payments', label: 'Pricing' },
]

const RESEARCH_TEAM_NAV: SiteNavLink = {
  href: '/research-team/applications',
  label: 'Research Team',
}

const FALLBACK_PROFILE_NAME = 'Instructor'

const studentSiteLinkClass =
  'whitespace-nowrap rounded-[10px] px-[9px] py-1.5 text-[13px] font-bold text-rs-body no-underline transition-colors duration-200 hover:bg-rs-sky-2 hover:text-rs-blue'

export function TeacherHeader() {
  const { user, signOut } = useAuthenticator((ctx) => [ctx.user, ctx.signOut])
  const { label: displayName, ready: displayNameReady } = useCognitoDisplayName(user?.username)
  const location = useLocation()
  const profileName = displayNameReady && displayName.trim() ? displayName : FALLBACK_PROFILE_NAME
  const [isAdmin, setIsAdmin] = useState(false)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const me = await fetchMe()
        if (!cancelled) {
          setIsAdmin(me.role.toLowerCase() === 'admin')
        }
      } catch {
        if (!cancelled) setIsAdmin(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const links = isAdmin ? [...TEACHER_NAV, RESEARCH_TEAM_NAV] : TEACHER_NAV

  const studentSiteLink = (
    <a
      href={studentSiteUrl}
      target="_blank"
      rel="noopener noreferrer"
      className={studentSiteLinkClass}
    >
      View Student Site
    </a>
  )

  return (
    <SiteHeader
      links={links}
      activePath={location.pathname}
      homeHref="/"
      badge={<Badge tone="blue">Instructor</Badge>}
      rightSlot={
        <>
          {studentSiteLink}
          <ProfileMenu
            name={profileName}
            subtitle="Instructor"
            items={[{ label: 'Sign out', onSelect: () => void signOut() }]}
          />
        </>
      }
      mobileCta={
        <>
          <Button
            href={studentSiteUrl}
            variant="ghost"
            size="sm"
            target="_blank"
            rel="noopener noreferrer"
          >
            View Student Site
          </Button>
          <Button type="button" variant="ghost" size="sm" onClick={() => void signOut()}>
            Sign out
          </Button>
        </>
      }
    />
  )
}
