import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

import { getPurchases } from '../../lib/api/billing'
import { listMyCertificates } from '../../lib/api/certificates'
import { getMyResearchTeam } from '../../lib/api/research-team'
import { fetchMe } from '../../lib/api/session'
import type { UserProfile } from '../../lib/api/types'
import { profileInitials } from '../../lib/profileInitials'
import { ownedCoursesFromPurchases } from '../../lib/ownedFromPurchases'
import { usePageReveal } from '../../components/auth/usePageReveal'
import {
  IconBook,
  IconCalendar,
  IconClock,
  IconMedal,
  IconPeople,
  IconUser,
} from './accountIcons'
import './AccountPage.css'

type LayoutSummary = {
  profile: UserProfile | null
  coursesOwned: number
  certificatesCount: number
  learningHours: number
  teamProgressPercent: number
}

function displayName(profile: UserProfile | null): string {
  if (!profile) return ''
  const parts = [profile.givenName, profile.familyName].map((p) => p?.trim()).filter(Boolean)
  if (parts.length > 0) return parts.join(' ')
  return profile.email?.trim() ?? ''
}

function formatMemberSince(iso: string | undefined): string {
  if (!iso?.trim()) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
}

function countOwnedCourses(purchases: Awaited<ReturnType<typeof getPurchases>>): number {
  const { ownsAllPublished, courseIds } = ownedCoursesFromPurchases(purchases)
  if (ownsAllPublished) return 4
  return courseIds.size
}

type ResearchTeamSnapshot = Awaited<ReturnType<typeof getMyResearchTeam>>

function teamProgressPercent(team: ResearchTeamSnapshot): number {
  if (team.courses.length === 0) return 0
  const done = team.courses.filter((course) => course.certified).length
  return Math.round((done / team.courses.length) * 100)
}

const tabClass = ({ isActive }: { isActive: boolean }) => (isActive ? 'active' : undefined)

export function AccountLayout() {
  const rootRef = useRef<HTMLDivElement>(null)
  usePageReveal(rootRef)
  const [summary, setSummary] = useState<LayoutSummary>({
    profile: null,
    coursesOwned: 0,
    certificatesCount: 0,
    learningHours: 0,
    teamProgressPercent: 0,
  })

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [profile, purchases, certificates, team] = await Promise.all([
          fetchMe(),
          getPurchases().catch(() => []),
          listMyCertificates()
            .then((payload) => payload.certificates.filter((row) => row.status !== 'revoked').length)
            .catch(() => 0),
          getMyResearchTeam().catch(
            (): ResearchTeamSnapshot => ({
              courses: [],
              eligible: false,
              canSubmit: false,
              application: null,
            }),
          ),
        ])
        if (cancelled) return
        setSummary({
          profile,
          coursesOwned: countOwnedCourses(purchases),
          certificatesCount: typeof certificates === 'number' ? certificates : 0,
          learningHours: 0,
          teamProgressPercent: teamProgressPercent(team),
        })
      } catch {
        if (!cancelled) setSummary((prev) => ({ ...prev, profile: null }))
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

  const profile = summary.profile

  return (
    <div className="pg-account" ref={rootRef}>
      <section className="dash-hero">
        <div className="wrap">
          <div className="acct-hero-grid">
            <div>
              <div className="dash-hi reveal">
                <IconUser />
                My Account
              </div>
              <h1 className="reveal acct-welcome-h1" data-d="1" id="account-profile-heading">
                Welcome back
              </h1>
              <p className="sub reveal" data-d="2">
                Manage your account, learning profile, certificates, and platform preferences.
              </p>
              <div className="member-since reveal" data-d="3">
                <IconCalendar />
                Member Since <span className="acct-join-date">{formatMemberSince(profile?.createdAt)}</span>
              </div>
            </div>
            <div className="acct-hero-card reveal" data-d="2">
              <div className="avatar-xl acct-avatar-text" aria-hidden>
                {profileInitials({
                  givenName: profile?.givenName,
                  familyName: profile?.familyName,
                  email: profile?.email,
                  displayName: displayName(profile),
                })}
              </div>
              <b className="acct-fullname">{displayName(profile)}</b>
              <span className="acct-role">Research Spectrum</span>
            </div>
          </div>
        </div>
      </section>

      <section className="db">
        <div className="wrap">
          <div className="stat-grid">
            <div className="stat reveal" data-d="1">
              <div className="si">
                <IconBook />
              </div>
              <div className="lbl">Courses Owned</div>
              <div className="val">{summary.coursesOwned}</div>
              <div className="vsub">active courses</div>
            </div>
            <div className="stat reveal" data-d="2">
              <div className="si">
                <IconMedal />
              </div>
              <div className="lbl">Certificates Earned</div>
              <div className="val">{summary.certificatesCount}</div>
              <div className="vsub">of 4 available</div>
            </div>
            <div className="stat reveal" data-d="3">
              <div className="si">
                <IconClock />
              </div>
              <div className="lbl">Learning Hours</div>
              <div className="val">{summary.learningHours}</div>
              <div className="vsub">hours completed</div>
            </div>
            <div className="stat featured reveal" data-d="4">
              <div className="si">
                <IconPeople />
              </div>
              <div className="lbl">Research Team Progress</div>
              <div className="val">{summary.teamProgressPercent}%</div>
              <div className="vsub">toward eligibility</div>
            </div>
          </div>
        </div>
      </section>

      <section className="db" style={{ paddingTop: 0 }}>
        <div className="wrap">
          <nav className="acct-tabs" aria-label="Account">
            <NavLink to="/account/profile" className={tabClass} end>
              Profile
            </NavLink>
            <NavLink to="/account/purchases" className={tabClass}>
              My purchases
            </NavLink>
          </nav>
        </div>
      </section>

      <Outlet />
    </div>
  )
}
