import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { Link, Navigate } from 'react-router-dom'

import { ArrowIcon } from '../components/auth/prototypeAuthParts'
import { usePageReveal } from '../components/auth/usePageReveal'
import { ApiError } from '../lib/api/client'
import {
  RESEARCH_TEAM_AREAS,
  RESEARCH_TEAM_EXPERIENCE_LEVELS,
  RESEARCH_TEAM_WEEKLY_HOURS,
  submitResearchTeamApplication,
  type ResearchTeamExperienceLevel,
  type ResearchTeamWeeklyHours,
} from '../lib/api/research-team'
import { fetchMe } from '../lib/api/session'
import { catalogApiUserMessage } from '../lib/apiUserMessages'
import { usePageTitle } from '../lib/page-title'
import { COUNTRIES } from '../lib/profile-options'
import { hasResearchTeamProfileFields } from '../lib/student-profile-research-team'
import './ApplyResearchTeamPage.css'

function submitErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 403 && err.code === 'not_eligible') {
      return 'You are not eligible to apply to the Research Team yet.'
    }
    if (err.status === 400 && err.code === 'email_required') {
      return 'Your account email is missing. Update your profile email, then try again.'
    }
    if (err.status === 409 && err.code === 'application_open') {
      return 'You already have an open application. Please wait for a decision.'
    }
    if (err.status === 409 && err.code === 'reapply_not_allowed') {
      return 'You cannot reapply at this time.'
    }
    if (err.status === 409 && err.code === 'already_accepted') {
      return 'You have already been accepted to the Research Team.'
    }
  }
  return catalogApiUserMessage(err)
}

function CheckBadgeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  )
}

function ClockIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </svg>
  )
}

export default function ApplyResearchTeamPage() {
  usePageTitle('Apply to Research Team')

  const rootRef = useRef<HTMLDivElement>(null)
  usePageReveal(rootRef)

  const [fullName, setFullName] = useState('')
  const [country, setCountry] = useState('')
  const [institution, setInstitution] = useState('')
  const [position, setPosition] = useState('')
  const [publicationCount, setPublicationCount] = useState('')
  const [projectCount, setProjectCount] = useState('')
  const [statsExperience, setStatsExperience] = useState<ResearchTeamExperienceLevel | ''>('')
  const [sysReviewExperience, setSysReviewExperience] = useState<ResearchTeamExperienceLevel | ''>(
    '',
  )
  const [interests, setInterests] = useState('')
  const [motivation, setMotivation] = useState('')
  const [weeklyHours, setWeeklyHours] = useState<ResearchTeamWeeklyHours | ''>('')
  const [researchAreas, setResearchAreas] = useState<string[]>([])
  const [acknowledgement, setAcknowledgement] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [profileLoading, setProfileLoading] = useState(true)
  const [needsProfileForApply, setNeedsProfileForApply] = useState(false)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const profile = await fetchMe()
        if (cancelled) return
        if (!hasResearchTeamProfileFields(profile)) {
          setNeedsProfileForApply(true)
          return
        }
        const given = (profile.givenName ?? '').trim()
        const family = (profile.familyName ?? '').trim()
        const name = [given, family].filter(Boolean).join(' ')
        if (name) setFullName(name)
        if (profile.country) setCountry(profile.country)
        if (profile.institution) setInstitution(profile.institution)
        if (profile.researchInterests) setInterests(profile.researchInterests)
        if (profile.profession) setPosition(profile.profession)
      } catch {
        /* Prefill is best-effort. */
      } finally {
        if (!cancelled) setProfileLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const canSubmit = useMemo(() => {
    if (!fullName.trim()) return false
    if (!country) return false
    if (!institution.trim()) return false
    if (!position.trim()) return false
    if (publicationCount.trim() === '' || Number.isNaN(Number(publicationCount))) return false
    if (projectCount.trim() === '' || Number.isNaN(Number(projectCount))) return false
    if (!statsExperience) return false
    if (!sysReviewExperience) return false
    if (!interests.trim()) return false
    if (!motivation.trim()) return false
    if (!weeklyHours) return false
    if (!acknowledgement) return false
    return true
  }, [
    fullName,
    country,
    institution,
    position,
    publicationCount,
    projectCount,
    statsExperience,
    sysReviewExperience,
    interests,
    motivation,
    weeklyHours,
    acknowledgement,
  ])

  function toggleArea(area: string) {
    setResearchAreas((prev) =>
      prev.includes(area) ? prev.filter((item) => item !== area) : [...prev, area],
    )
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (!canSubmit || submitting || success) return
    if (!statsExperience || !sysReviewExperience || !weeklyHours) return
    setError(null)
    setSubmitting(true)
    try {
      await submitResearchTeamApplication({
        fullName: fullName.trim(),
        country,
        institution: institution.trim(),
        position: position.trim(),
        publicationCount: Math.trunc(Number(publicationCount)),
        projectCount: Math.trunc(Number(projectCount)),
        statsExperience,
        sysReviewExperience,
        interests: interests.trim(),
        motivation: motivation.trim(),
        weeklyHours,
        acknowledgement: true,
        researchAreas: researchAreas.length > 0 ? researchAreas : undefined,
      })
      setSuccess(true)
    } catch (err) {
      setError(submitErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  if (needsProfileForApply) {
    return <Navigate to="/account/profile?complete=research-team" replace />
  }

  return (
    <div
      ref={rootRef}
      className="pg-apply-research-team"
      data-testid="student-page-apply-research-team"
    >
      <section className="rt-hero art-hero">
        <div className="wrap">
          <div className="art-hero-inner">
            <div className="eyebrow reveal" style={{ margin: '0 auto 18px' }}>
              <span className="dot" aria-hidden="true" />
              Research Spectrum Program
            </div>
            <h1 className="reveal" data-d="1">
              Apply to the
              <br />
              <span className="g">Research Team</span>
            </h1>
            <p className="sub reveal" data-d="2" id="art-hero-sub">
              You&apos;ve completed every eligibility requirement — the next step is to tell us about
              yourself and the research you&apos;d like to contribute to.
            </p>
          </div>
        </div>
      </section>

      <section className="af-section">
        <div className="wrap">
          <div className="af-grid">
            <div className="af-card reveal">
              <h2 className="af-h">Research Team Application</h2>
              <p className="af-sub">
                Please complete every field below. This information helps the Research Spectrum team
                match you to active research projects.
              </p>

              {profileLoading ? (
                <p className="af-loading" role="status">
                  Loading your profile…
                </p>
              ) : null}

              {success ? (
                <div className="af-success" role="status">
                  <p>Your application has been submitted. We will review it shortly.</p>
                  <Link to="/research-team">Back to Research Team</Link>
                </div>
              ) : null}

              {!profileLoading && !success ? (
                <form id="rt-apply-form" onSubmit={onSubmit} noValidate>
                  <fieldset className="af-fieldset">
                    <h3>Personal Information</h3>
                    <div className="af-row">
                      <div className="af-field">
                        <label htmlFor="af-fullname">Full Name</label>
                        <input
                          id="af-fullname"
                          name="fullName"
                          type="text"
                          autoComplete="name"
                          placeholder="e.g. Sara Al-Khatib"
                          value={fullName}
                          onChange={(e) => setFullName(e.target.value)}
                          required
                        />
                      </div>
                      <div className="af-field">
                        <label htmlFor="af-country">Country</label>
                        <select
                          id="af-country"
                          name="country"
                          autoComplete="country-name"
                          value={country}
                          onChange={(e) => setCountry(e.target.value)}
                          required
                        >
                          <option value="">Select a country</option>
                          {COUNTRIES.map((item) => (
                            <option key={item} value={item}>
                              {item}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <div className="af-row">
                      <div className="af-field">
                        <label htmlFor="af-institution">Current Institution</label>
                        <input
                          id="af-institution"
                          name="institution"
                          type="text"
                          placeholder="e.g. University of Jordan"
                          value={institution}
                          onChange={(e) => setInstitution(e.target.value)}
                          required
                        />
                      </div>
                      <div className="af-field">
                        <label htmlFor="af-position">Current Position</label>
                        <input
                          id="af-position"
                          name="position"
                          type="text"
                          placeholder="e.g. Medical Student, Resident, Research Assistant"
                          value={position}
                          onChange={(e) => setPosition(e.target.value)}
                          required
                        />
                      </div>
                    </div>
                  </fieldset>

                  <fieldset className="af-fieldset">
                    <h3>Research Experience</h3>
                    <div className="af-row">
                      <div className="af-field">
                        <label htmlFor="af-publications">Number of Publications</label>
                        <input
                          id="af-publications"
                          name="publications"
                          type="number"
                          min={0}
                          max={9999}
                          inputMode="numeric"
                          placeholder="0"
                          value={publicationCount}
                          onChange={(e) => setPublicationCount(e.target.value)}
                          required
                        />
                      </div>
                      <div className="af-field">
                        <label htmlFor="af-projects">Number of Research Projects</label>
                        <input
                          id="af-projects"
                          name="projects"
                          type="number"
                          min={0}
                          max={9999}
                          inputMode="numeric"
                          placeholder="0"
                          value={projectCount}
                          onChange={(e) => setProjectCount(e.target.value)}
                          required
                        />
                      </div>
                    </div>
                    <div className="af-row">
                      <div className="af-field">
                        <label htmlFor="af-stats-exp">Statistical Analysis Experience</label>
                        <select
                          id="af-stats-exp"
                          name="statsExperience"
                          value={statsExperience}
                          onChange={(e) =>
                            setStatsExperience(e.target.value as ResearchTeamExperienceLevel | '')
                          }
                          required
                        >
                          <option value="">Select an option</option>
                          {RESEARCH_TEAM_EXPERIENCE_LEVELS.map((level) => (
                            <option key={level} value={level}>
                              {level}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="af-field">
                        <label htmlFor="af-sysreview-exp">Systematic Review Experience</label>
                        <select
                          id="af-sysreview-exp"
                          name="sysReviewExperience"
                          value={sysReviewExperience}
                          onChange={(e) =>
                            setSysReviewExperience(e.target.value as ResearchTeamExperienceLevel | '')
                          }
                          required
                        >
                          <option value="">Select an option</option>
                          {RESEARCH_TEAM_EXPERIENCE_LEVELS.map((level) => (
                            <option key={level} value={level}>
                              {level}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  </fieldset>

                  <fieldset className="af-fieldset">
                    <h3>Research Areas Of Interest</h3>
                    <p className="af-sub" style={{ marginBottom: 0 }}>
                      Select all areas that interest you. You can provide additional details below.
                    </p>
                    <div className="af-checkgrid">
                      {RESEARCH_TEAM_AREAS.map((area) => (
                        <label key={area} className="af-check-option">
                          <input
                            type="checkbox"
                            name="researchAreas"
                            value={area}
                            checked={researchAreas.includes(area)}
                            onChange={() => toggleArea(area)}
                          />
                          {area}
                        </label>
                      ))}
                    </div>
                  </fieldset>

                  <fieldset className="af-fieldset">
                    <h3>Research Interests</h3>
                    <div className="af-row full">
                      <div className="af-field">
                        <label htmlFor="af-interests">
                          Tell Us More About Your Research Interests
                        </label>
                        <textarea
                          id="af-interests"
                          name="interests"
                          placeholder="Describe specific topics, specialties, populations, diseases, or research questions that particularly interest you."
                          value={interests}
                          onChange={(e) => setInterests(e.target.value)}
                          required
                        />
                      </div>
                    </div>
                  </fieldset>

                  <fieldset className="af-fieldset">
                    <h3>Motivation</h3>
                    <div className="af-row full">
                      <div className="af-field">
                        <label htmlFor="af-motivation">
                          Why do you want to join the Research Spectrum Research Team?
                        </label>
                        <textarea
                          id="af-motivation"
                          name="motivation"
                          className="af-motivation"
                          placeholder="Tell us about your goals, what you hope to contribute, and what you hope to learn..."
                          value={motivation}
                          onChange={(e) => setMotivation(e.target.value)}
                          required
                        />
                      </div>
                    </div>
                  </fieldset>

                  <fieldset className="af-fieldset" style={{ marginBottom: 0 }}>
                    <h3>Availability</h3>
                    <div className="af-row full">
                      <div className="af-field">
                        <label htmlFor="af-availability">
                          How many hours per week can you dedicate to Research Team projects?
                        </label>
                        <select
                          id="af-availability"
                          name="availability"
                          value={weeklyHours}
                          onChange={(e) =>
                            setWeeklyHours(e.target.value as ResearchTeamWeeklyHours | '')
                          }
                          required
                        >
                          <option value="">Select an option</option>
                          {RESEARCH_TEAM_WEEKLY_HOURS.map((hours) => (
                            <option key={hours} value={hours}>
                              {hours}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <div className="af-checkbox">
                      <input
                        type="checkbox"
                        id="af-agree"
                        name="agreement"
                        checked={acknowledgement}
                        onChange={(e) => setAcknowledgement(e.target.checked)}
                      />
                      <label htmlFor="af-agree">
                        I understand that eligibility does not guarantee selection and that Research
                        Spectrum may accept or reject applications based on project needs and
                        evaluation criteria.
                      </label>
                    </div>
                  </fieldset>

                  {error ? (
                    <p className="af-error" id="rt-apply-error" role="alert">
                      {error}
                    </p>
                  ) : null}

                  <div className="af-submit-row">
                    <button
                      type="submit"
                      className={`btn btn-primary${!canSubmit || submitting ? ' btn-disabled' : ''}`}
                      disabled={!canSubmit || submitting}
                    >
                      {submitting ? 'Submitting…' : 'Submit Application'}
                      {!submitting ? <ArrowIcon /> : null}
                    </button>
                    <Link to="/research-team" className="btn btn-ghost">
                      Cancel
                    </Link>
                  </div>
                </form>
              ) : null}
            </div>

            <aside className="af-side">
              <div className="rt-hero-card reveal">
                <h3>Your Status</h3>
                <div className="rt-status-badge rtb-eligible" id="art-status-badge">
                  <CheckBadgeIcon />
                  Eligible To Apply
                </div>
                <p className="rt-side-desc" id="art-status-desc">
                  You&apos;ve completed all four Research Spectrum certificates: Research
                  Methodology, Statistics &amp; SPSS, Scientific Writing, and Systematic Reviews
                  &amp; Meta-Analysis.
                </p>
              </div>
              <div className="rt-card reveal">
                <div className="rc-icon">
                  <ClockIcon />
                </div>
                <h3>What Happens Next?</h3>
                <p>
                  Once submitted, your application status will update to <strong>Submitted</strong>{' '}
                  on the Research Team page. Applications are reviewed on a rolling basis — you&apos;ll
                  be notified of any status changes (Under Review, Interview, Accepted, or Not
                  Selected) right there.
                </p>
              </div>
            </aside>
          </div>
        </div>
      </section>
    </div>
  )
}
