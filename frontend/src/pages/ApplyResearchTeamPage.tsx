import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '../components/ui/Button'
import { Field } from '../components/ui/Field'
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

export default function ApplyResearchTeamPage() {
  usePageTitle('Apply to Research Team')

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

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const profile = await fetchMe()
        if (cancelled) return
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

  const selectClass =
    'w-full rounded-xl border-[1.5px] border-solid border-rs-line bg-white px-[14px] py-[11px] text-[15px] text-rs-ink outline-none transition duration-200 ease-rs focus:border-rs-blue focus:shadow-[0_0_0_3px_rgba(30,94,255,.10)]'

  const textareaClass =
    'w-full min-h-[110px] rounded-xl border-[1.5px] border-solid border-rs-line bg-white px-[14px] py-[11px] text-[15px] text-rs-ink outline-none transition duration-200 ease-rs focus:border-rs-blue focus:shadow-[0_0_0_3px_rgba(30,94,255,.10)]'

  return (
    <div className="min-h-screen bg-white text-rs-ink" data-testid="student-page-apply-research-team">
      <section className="px-5 py-10 sm:px-7 sm:py-14">
        <div className="mx-auto max-w-2xl">
          <h1 className="text-3xl font-extrabold tracking-tight text-rs-ink sm:text-4xl">
            Apply to the Research Team
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-rs-body">
            Tell us about your background and research interests. Required fields must be completed
            before you can submit.
          </p>

          {profileLoading ? (
            <p className="mt-8 text-sm text-rs-body">Loading your profile…</p>
          ) : null}

          {success ? (
            <div
              className="mt-8 rounded-rs border border-[#bce7c8] bg-[#dcf5e3] px-5 py-4"
              role="status"
            >
              <p className="text-sm font-semibold text-[#0d6f3e]">
                Your application has been submitted. We will review it shortly.
              </p>
              <Link
                to="/research-team"
                className="mt-3 inline-flex min-h-11 items-center text-sm font-bold text-rs-blue"
              >
                Back to Research Team
              </Link>
            </div>
          ) : null}

          {!profileLoading && !success ? (
            <form className="mt-8 space-y-1" onSubmit={onSubmit} noValidate>
              <Field
                label="Full name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                autoComplete="name"
                required
              />

              <Field label="Country">
                <select
                  className={selectClass}
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
              </Field>

              <Field
                label="Institution"
                value={institution}
                onChange={(e) => setInstitution(e.target.value)}
                required
              />

              <Field
                label="Position"
                value={position}
                onChange={(e) => setPosition(e.target.value)}
                required
              />

              <Field
                label="Publication count"
                type="number"
                min={0}
                max={9999}
                inputMode="numeric"
                value={publicationCount}
                onChange={(e) => setPublicationCount(e.target.value)}
                required
              />

              <Field
                label="Project count"
                type="number"
                min={0}
                max={9999}
                inputMode="numeric"
                value={projectCount}
                onChange={(e) => setProjectCount(e.target.value)}
                required
              />

              <Field label="Statistics experience">
                <select
                  className={selectClass}
                  value={statsExperience}
                  onChange={(e) =>
                    setStatsExperience(e.target.value as ResearchTeamExperienceLevel | '')
                  }
                  required
                >
                  <option value="">Select level</option>
                  {RESEARCH_TEAM_EXPERIENCE_LEVELS.map((level) => (
                    <option key={level} value={level}>
                      {level}
                    </option>
                  ))}
                </select>
              </Field>

              <Field label="Systematic review experience">
                <select
                  className={selectClass}
                  value={sysReviewExperience}
                  onChange={(e) =>
                    setSysReviewExperience(e.target.value as ResearchTeamExperienceLevel | '')
                  }
                  required
                >
                  <option value="">Select level</option>
                  {RESEARCH_TEAM_EXPERIENCE_LEVELS.map((level) => (
                    <option key={level} value={level}>
                      {level}
                    </option>
                  ))}
                </select>
              </Field>

              <Field label="Interests">
                <textarea
                  className={textareaClass}
                  value={interests}
                  onChange={(e) => setInterests(e.target.value)}
                  required
                />
              </Field>

              <Field label="Motivation">
                <textarea
                  className={textareaClass}
                  value={motivation}
                  onChange={(e) => setMotivation(e.target.value)}
                  required
                />
              </Field>

              <Field label="Weekly hours">
                <select
                  className={selectClass}
                  value={weeklyHours}
                  onChange={(e) => setWeeklyHours(e.target.value as ResearchTeamWeeklyHours | '')}
                  required
                >
                  <option value="">Select weekly hours</option>
                  {RESEARCH_TEAM_WEEKLY_HOURS.map((hours) => (
                    <option key={hours} value={hours}>
                      {hours}
                    </option>
                  ))}
                </select>
              </Field>

              <fieldset className="mb-4">
                <legend className="mb-2 block text-[13px] font-bold tracking-[-0.005em] text-rs-navy">
                  Research areas (optional)
                </legend>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {RESEARCH_TEAM_AREAS.map((area) => (
                    <label
                      key={area}
                      className="flex min-h-11 cursor-pointer items-center gap-2.5 rounded-xl border border-rs-line px-3 py-2 text-sm text-rs-ink"
                    >
                      <input
                        type="checkbox"
                        className="size-4 shrink-0 accent-rs-blue"
                        checked={researchAreas.includes(area)}
                        onChange={() => toggleArea(area)}
                      />
                      <span>{area}</span>
                    </label>
                  ))}
                </div>
              </fieldset>

              <label className="mb-6 flex min-h-11 cursor-pointer items-start gap-3 rounded-xl border border-rs-line px-4 py-3 text-sm text-rs-ink">
                <input
                  type="checkbox"
                  className="mt-0.5 size-4 shrink-0 accent-rs-blue"
                  checked={acknowledgement}
                  onChange={(e) => setAcknowledgement(e.target.checked)}
                  aria-label="I acknowledge that eligibility does not guarantee acceptance"
                />
                <span>
                  I acknowledge that eligibility does not guarantee acceptance and that my
                  application will be reviewed by the Research Team.
                </span>
              </label>

              {error ? (
                <p className="mb-4 text-sm font-semibold text-[#b91c1c]" role="alert">
                  {error}
                </p>
              ) : null}

              <div className="flex flex-wrap items-center gap-3">
                <Button type="submit" disabled={!canSubmit || submitting}>
                  {submitting ? 'Submitting…' : 'Submit application'}
                </Button>
                <Button to="/research-team" variant="ghost">
                  Cancel
                </Button>
              </div>
            </form>
          ) : null}
        </div>
      </section>
    </div>
  )
}
