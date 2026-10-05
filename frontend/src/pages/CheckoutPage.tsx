import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import instructorPhoto from '../assets/prototype/instructor.jpg'
import { usePageReveal } from '../components/auth/usePageReveal'
import { createCheckoutSession, getBundle, getPurchases } from '../lib/api/billing'
import { getCourse } from '../lib/api/catalog'
import { listPublishedCourses, type PublicCatalogCourse } from '../lib/api/public-catalog'
import { hasSignedInIdToken } from '../lib/api/session'
import type { CheckoutProductType } from '../lib/api/types'
import { catalogApiUserMessage } from '../lib/apiUserMessages'
import { displayNameFromAttributes, loadMergedProfileAttributes } from '../lib/cognito-display-name'
import { formatUsdMinor } from '../lib/formatUsdMinor'
import { isHttpsUrl } from '../lib/isHttpsUrl'
import { ownedCoursesFromPurchases } from '../lib/ownedFromPurchases'
import { usePageTitle } from '../lib/page-title'
import { checkoutLoadingLabel } from '../lib/purchaseCopy'
import { persistReturnPathBeforeHostedUi } from '../lib/post-login-return'
import './CheckoutPage.css'

type CheckoutParams =
  | { productType: 'bundle' }
  | { productType: 'course'; courseId: string }

const TITLE_ORDER = [
  'research methodology',
  'statistics & spss',
  'scientific writing',
  'systematic reviews & meta-analysis',
]

const CHECKOUT_COUNTRIES = [
  'Jordan',
  'United States',
  'United Kingdom',
  'Canada',
  'Saudi Arabia',
  'United Arab Emirates',
  'Germany',
  'France',
  'Australia',
  'India',
  'Other',
] as const

const CHECKOUT_FAQ: { q: string; a: ReactNode }[] = [
  {
    q: 'Do I get lifetime access?',
    a: 'Yes. All Research Spectrum courses include lifetime access for as long as the course remains available. Work through the material at your own pace and return to any module at any time — including future course updates.',
  },
  {
    q: 'How do certificates work?',
    a: 'Each course awards a Competency-Based Certificate of Completion upon passing all module quizzes and the graded final assignment. Certificates carry a unique credential ID and are publicly verifiable. Holding all four certificates makes you eligible to apply for the Research Team.',
  },
  {
    q: 'Can I apply to the Research Team?',
    a: 'Yes. Completing all four courses and earning their certificates makes you eligible to apply for the Research Spectrum Research Team — where members contribute to peer-reviewed publications under faculty mentorship. The Research Mastery Bundle is the fastest pathway to eligibility.',
  },
  {
    q: 'What payment methods are supported?',
    a: 'We accept credit and debit cards (Visa, Mastercard, American Express) and HyperPay. All transactions are encrypted and Research Spectrum does not store card details.',
  },
  {
    q: 'What is the refund policy?',
    a: (
      <>
        All purchases are final per our{' '}
        <Link to="/refund" style={{ color: 'var(--blue)', fontWeight: 700 }}>
          Refund Policy
        </Link>{' '}
        — access begins immediately upon payment. If you have questions before purchasing, please{' '}
        <Link to="/contact" style={{ color: 'var(--blue)', fontWeight: 700 }}>
          contact us
        </Link>
        .
      </>
    ),
  },
]

function parseCheckoutParams(searchParams: URLSearchParams): CheckoutParams | null {
  const productType = (searchParams.get('productType') ?? '').trim().toLowerCase()
  if (productType === 'bundle') {
    return { productType: 'bundle' }
  }
  if (productType === 'course') {
    const courseId = (searchParams.get('courseId') ?? '').trim()
    if (!courseId) return null
    return { productType: 'course', courseId }
  }
  return null
}

function byCatalogOrder(courses: PublicCatalogCourse[]): PublicCatalogCourse[] {
  const rank = (title: string) => TITLE_ORDER.indexOf(title.trim().toLowerCase())
  return courses
    .map((course, index) => ({ course, index, rank: rank(course.title) }))
    .filter((item) => item.rank !== -1)
    .sort((a, b) => a.rank - b.rank || a.index - b.index)
    .map((item) => item.course)
}

function dollars(amountMinor: number | null | undefined): string | null {
  if (typeof amountMinor !== 'number' || !Number.isFinite(amountMinor) || amountMinor <= 0) return null
  const formatted = formatUsdMinor(amountMinor)
  if (amountMinor % 100 === 0) return formatted.replace(/\.00$/, '')
  return formatted
}

function Icon({ children, strokeWidth = '2' }: { children: ReactNode; strokeWidth?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  )
}

function CheckIcon({ strokeWidth = '2.8' }: { strokeWidth?: string }) {
  return (
    <Icon strokeWidth={strokeWidth}>
      <path d="M20 6 9 17l-5-5" />
    </Icon>
  )
}

function ArrowIcon() {
  return (
    <Icon strokeWidth="2.5">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </Icon>
  )
}

export default function CheckoutPage() {
  usePageTitle('Checkout')
  const rootRef = useRef<HTMLDivElement>(null)
  usePageReveal(rootRef)

  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const checkoutParams = useMemo(() => parseCheckoutParams(searchParams), [searchParams])

  const [signedIn, setSignedIn] = useState<boolean | null>(null)
  const [catalogCourses, setCatalogCourses] = useState<PublicCatalogCourse[]>([])
  const [bundleAmountMinor, setBundleAmountMinor] = useState<number | null>(null)
  const [courseTitle, setCourseTitle] = useState('')
  const [courseAmountMinor, setCourseAmountMinor] = useState<number | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [ownedAll, setOwnedAll] = useState(false)
  const [ownedCourseIds, setOwnedCourseIds] = useState<Set<string>>(() => new Set())

  const [billName, setBillName] = useState('')
  const [billCountry, setBillCountry] = useState('')
  const [payMethod, setPayMethod] = useState<'card' | 'hyperpay'>('card')
  const [termsOk, setTermsOk] = useState(false)
  const [privacyOk, setPrivacyOk] = useState(false)
  const [refundOk, setRefundOk] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<{ name?: string; country?: string }>({})
  const [checkboxErrors, setCheckboxErrors] = useState<{ terms?: boolean; privacy?: boolean; refund?: boolean }>({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [openFaq, setOpenFaq] = useState<number | null>(null)

  const orderedCourses = useMemo(() => byCatalogOrder(catalogCourses), [catalogCourses])

  useEffect(() => {
    let cancelled = false
    void hasSignedInIdToken().then((ok) => {
      if (!cancelled) setSignedIn(ok)
    })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    void listPublishedCourses()
      .then((courses) => {
        if (!cancelled) setCatalogCourses(byCatalogOrder(courses))
      })
      .catch(() => {
        if (!cancelled) setCatalogCourses([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    void getBundle()
      .then((offer) => {
        if (!cancelled) setBundleAmountMinor(offer.amountMinor)
      })
      .catch(() => {
        if (!cancelled) setBundleAmountMinor(null)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (signedIn !== true) return
    let cancelled = false
    void loadMergedProfileAttributes()
      .then((attrs) => {
        if (cancelled) return
        const username = attrs.email?.trim() || attrs.name?.trim() || 'Student'
        const name = displayNameFromAttributes(attrs, username)
        if (name) setBillName((prev) => prev || name)
      })
      .catch(() => undefined)
    void getPurchases()
      .then((purchases) => {
        if (cancelled) return
        const owned = ownedCoursesFromPurchases(purchases)
        setOwnedAll(owned.ownsAllPublished)
        setOwnedCourseIds(owned.courseIds)
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [signedIn])

  useEffect(() => {
    if (!checkoutParams) return
    let cancelled = false
    setLoadError(null)
    setCourseTitle('')
    setCourseAmountMinor(null)

    if (checkoutParams.productType === 'bundle') {
      return () => {
        cancelled = true
      }
    }

    void (async () => {
      try {
        const course = await getCourse(checkoutParams.courseId)
        if (cancelled) return
        setCourseTitle(course.title)
        if (typeof course.amountMinor === 'number' && course.amountMinor > 0) {
          setCourseAmountMinor(course.amountMinor)
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(catalogApiUserMessage(err, 'loadCourse'))
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [checkoutParams])

  const isBundle = checkoutParams?.productType === 'bundle'
  const activeCourseId = checkoutParams?.productType === 'course' ? checkoutParams.courseId : null

  const productLabel = isBundle ? 'Research Mastery Bundle' : courseTitle || 'Course'
  const priceMinor = isBundle ? bundleAmountMinor : courseAmountMinor

  const sumCourseMinor = useMemo(() => {
    let sum = 0
    for (const course of orderedCourses) {
      if (typeof course.amountMinor !== 'number' || course.amountMinor <= 0) return null
      sum += course.amountMinor
    }
    return orderedCourses.length === 4 ? sum : null
  }, [orderedCourses])

  const origMinor = isBundle ? sumCourseMinor : null
  const discountMinor =
    isBundle && origMinor != null && priceMinor != null && origMinor > priceMinor
      ? origMinor - priceMinor
      : null

  const priceLabel = dollars(priceMinor)
  const origLabel = origMinor != null ? dollars(origMinor) : null
  const discountLabel = discountMinor != null ? dollars(discountMinor) : null

  const alreadyOwned = useMemo(() => {
    if (!checkoutParams) return false
    if (checkoutParams.productType === 'bundle') return ownedAll
    if (ownedAll) return true
    return ownedCourseIds.has(checkoutParams.courseId)
  }, [checkoutParams, ownedAll, ownedCourseIds])

  const includesCourses = isBundle
    ? orderedCourses.map((c) => c.title)
    : courseTitle
      ? [courseTitle]
      : []

  const onSignIn = useCallback(() => {
    persistReturnPathBeforeHostedUi()
    navigate('/login')
  }, [navigate])

  const selectProduct = useCallback(
    (courseId: string | 'bundle') => {
      if (courseId === 'bundle') {
        navigate('/checkout?productType=bundle')
        return
      }
      navigate(`/checkout?productType=course&courseId=${encodeURIComponent(courseId)}`)
    },
    [navigate],
  )

  const onSubmit = useCallback(async () => {
    if (!checkoutParams || signedIn !== true || alreadyOwned) return

    const nextFieldErrors: { name?: string; country?: string } = {}
    const nextCheckboxErrors: { terms?: boolean; privacy?: boolean; refund?: boolean } = {}
    if (!billName.trim()) nextFieldErrors.name = 'Please enter your full name.'
    if (!billCountry) nextFieldErrors.country = 'Please select your country.'
    if (!termsOk) nextCheckboxErrors.terms = true
    if (!privacyOk) nextCheckboxErrors.privacy = true
    if (!refundOk) nextCheckboxErrors.refund = true

    setFieldErrors(nextFieldErrors)
    setCheckboxErrors(nextCheckboxErrors)

    if (
      nextFieldErrors.name ||
      nextFieldErrors.country ||
      nextCheckboxErrors.terms ||
      nextCheckboxErrors.privacy ||
      nextCheckboxErrors.refund
    ) {
      setSubmitError('Please complete all required fields and confirmations.')
      return
    }

    setSubmitting(true)
    setSubmitError(null)
    try {
      const body =
        checkoutParams.productType === 'bundle'
          ? { productType: 'bundle' as CheckoutProductType }
          : {
              productType: 'course' as CheckoutProductType,
              courseId: checkoutParams.courseId,
            }
      const { redirect_url } = await createCheckoutSession(body)
      if (!isHttpsUrl(redirect_url)) {
        setSubmitError(catalogApiUserMessage(new Error('invalid redirect'), 'checkout'))
        return
      }
      window.location.href = redirect_url
    } catch (err) {
      setSubmitError(catalogApiUserMessage(err, 'checkout'))
    } finally {
      setSubmitting(false)
    }
  }, [
    alreadyOwned,
    billCountry,
    billName,
    checkoutParams,
    privacyOk,
    refundOk,
    signedIn,
    termsOk,
  ])

  const submitLabel = alreadyOwned
    ? 'Already Enrolled'
    : submitting
      ? checkoutLoadingLabel
      : priceLabel
        ? `Complete Purchase — ${priceLabel}`
        : 'Complete Purchase'

  if (!checkoutParams) {
    return (
      <div className="pg-checkout" data-testid="checkout-page">
        <div className="wrap" style={{ padding: '72px 0' }}>
          <h1 className="title" style={{ textAlign: 'left', fontSize: '2rem' }}>
            Checkout
          </h1>
          <p style={{ marginTop: 12, color: 'var(--body)' }}>
            This checkout link is invalid. Choose a course or bundle from the catalog.
          </p>
          <Link to="/courses" className="btn btn-primary" style={{ marginTop: 24 }}>
            Browse courses
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div ref={rootRef} className="pg-checkout" data-testid="checkout-page">
      <section className="co-hero">
        <div className="wrap">
          <div className="co-hero-grid">
            <div className="hero-copy">
              <div className="eyebrow reveal">
                <span className="dot" />
                Secure Checkout
              </div>
              <h1 className="reveal" data-d="1">
                Complete Your
                <br />
                <span className="g">Enrollment</span>
              </h1>
              <p className="sub reveal" data-d="2">
                You&apos;re one step away from gaining access to Research Spectrum&apos;s comprehensive research
                education curriculum.
              </p>
              <ul className="trust-list reveal" data-d="3">
                {[
                  'Secure payment processing',
                  'Lifetime course access',
                  'Competency-Based Certificate of Completion',
                  'Learn at your own pace',
                ].map((item) => (
                  <li key={item}>
                    <span className="ck">
                      <CheckIcon />
                    </span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div className="reveal" data-d="2">
              <div className="hero-summary-card">
                <div className="hsc-badge">
                  <Icon strokeWidth="2.5">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                    <path d="M9 12l2 2 4-4" />
                  </Icon>
                  Selected Enrollment
                </div>
                <div className="hsc-product">{productLabel}</div>
                <div className="hsc-price">
                  {origLabel && isBundle ? <span className="orig">{origLabel}</span> : null}
                  <span>{priceLabel ?? '…'}</span>
                </div>
                <div className="hsc-divider" />
                <div className="hsc-row">
                  <Icon>
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </Icon>
                  Lifetime Access
                </div>
                <div className="hsc-row">
                  <Icon>
                    <circle cx="12" cy="8" r="6" />
                    <path d="M9 13.8 7 22l5-3 5 3-2-8.2" />
                  </Icon>
                  Certificate of Completion
                </div>
                <div className="hsc-row">
                  <Icon>
                    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                    <circle cx="9" cy="7" r="4" />
                    <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
                  </Icon>
                  Research Team Pathway
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="wrap">
        <div style={{ paddingTop: 44 }}>
          <p
            style={{
              fontSize: 13,
              fontWeight: 800,
              textTransform: 'uppercase',
              letterSpacing: '.09em',
              color: 'var(--muted)',
              marginBottom: 14,
              textAlign: 'center',
            }}
          >
            Select Your Program
          </p>
          <div className="prod-switcher">
            {orderedCourses.map((course) => {
              const active = activeCourseId === course.id
              const price = dollars(course.amountMinor)
              return (
                <button
                  key={course.id}
                  type="button"
                  className={`prod-btn${active ? ' active' : ''}`}
                  onClick={() => selectProduct(course.id)}
                >
                  <div className="pb-label">{course.title}</div>
                  <div className="pb-price">{price ?? '…'}</div>
                </button>
              )
            })}
            <button
              type="button"
              className={`prod-btn${isBundle ? ' active' : ''}`}
              onClick={() => selectProduct('bundle')}
            >
              <div className="pb-badge">Best Value</div>
              <div className="pb-label">Research Mastery Bundle</div>
              <div className="pb-price">{dollars(bundleAmountMinor) ?? '…'}</div>
            </button>
          </div>
        </div>

        <div className="checkout-layout">
          <div>
            {signedIn === false ? (
              <div className="form-card" style={{ marginBottom: 16 }}>
                <div className="fc-section">
                  <p className="acc-info-box">
                    <b>Sign in required.</b> Link this purchase to your account before payment.
                  </p>
                  <button type="button" className="btn btn-primary" style={{ width: '100%' }} onClick={onSignIn}>
                    Sign in to continue
                  </button>
                </div>
              </div>
            ) : null}

            <div className="form-card" style={{ marginBottom: 16 }}>
              <div className="fc-section">
                <div className="fc-sec-head">
                  <div className="fc-sec-num">1</div>
                  <div className="fc-sec-title">Billing Information</div>
                </div>
                <div className="field-grid">
                  <div className={`field${fieldErrors.name ? ' has-err' : ''}`}>
                    <label htmlFor="billName">Full Name</label>
                    <input
                      id="billName"
                      type="text"
                      placeholder="Your full name"
                      autoComplete="name"
                      value={billName}
                      onChange={(e) => setBillName(e.target.value)}
                      disabled={signedIn !== true}
                    />
                    {fieldErrors.name ? <span className="err-msg">{fieldErrors.name}</span> : null}
                  </div>
                  <div className={`field${fieldErrors.country ? ' has-err' : ''}`}>
                    <label htmlFor="billCountry">Country</label>
                    <select
                      id="billCountry"
                      value={billCountry}
                      onChange={(e) => setBillCountry(e.target.value)}
                      disabled={signedIn !== true}
                    >
                      <option value="">Select…</option>
                      {CHECKOUT_COUNTRIES.map((country) => (
                        <option key={country} value={country}>
                          {country}
                        </option>
                      ))}
                    </select>
                    {fieldErrors.country ? <span className="err-msg">{fieldErrors.country}</span> : null}
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="billInstitution">
                    Institution <span className="field-opt">(optional)</span>
                  </label>
                  <input id="billInstitution" type="text" placeholder="e.g. University of Jordan" autoComplete="organization" disabled={signedIn !== true} />
                </div>
                <div className="field">
                  <label htmlFor="billReferral">
                    How did you hear about us? <span className="field-opt">(optional)</span>
                  </label>
                  <select id="billReferral" defaultValue="" disabled={signedIn !== true}>
                    <option value="">Select…</option>
                    <option>Social media</option>
                    <option>Friend or colleague</option>
                    <option>Search engine</option>
                    <option>Instagram</option>
                    <option>WhatsApp</option>
                    <option>University or hospital</option>
                    <option>Other</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="form-card" style={{ marginBottom: 16 }}>
              <div className="fc-section">
                <div className="fc-sec-head">
                  <div className="fc-sec-num">2</div>
                  <div className="fc-sec-title">Payment Method</div>
                </div>
                <div className="payment-methods">
                  <label className={`pay-opt${payMethod === 'card' ? ' selected' : ''}`}>
                    <input
                      type="radio"
                      name="payMethod"
                      value="card"
                      checked={payMethod === 'card'}
                      onChange={() => setPayMethod('card')}
                      disabled={signedIn !== true}
                    />
                    <div className="pay-opt-icon">CARD</div>
                    <div className="pay-opt-label">
                      <b>Credit / Debit Card</b>
                      <span>Visa, Mastercard, American Express</span>
                    </div>
                    <span className="pay-opt-badge">Recommended</span>
                  </label>
                  <label className={`pay-opt${payMethod === 'hyperpay' ? ' selected' : ''}`}>
                    <input
                      type="radio"
                      name="payMethod"
                      value="hyperpay"
                      checked={payMethod === 'hyperpay'}
                      onChange={() => setPayMethod('hyperpay')}
                      disabled={signedIn !== true}
                    />
                    <div className="pay-opt-icon" style={{ fontSize: '8.5px' }}>
                      HYPER
                      <br />
                      PAY
                    </div>
                    <div className="pay-opt-label">
                      <b>HyperPay</b>
                      <span>Middle East payment gateway</span>
                    </div>
                  </label>
                </div>
                {payMethod === 'card' ? (
                  <div className="card-fields show">
                    <div className="field" style={{ marginBottom: 0 }}>
                      <label
                        style={{
                          fontSize: '12.5px',
                          marginBottom: 6,
                          display: 'block',
                          fontWeight: 700,
                          color: 'var(--muted)',
                          textTransform: 'uppercase',
                          letterSpacing: '.07em',
                        }}
                      >
                        Card Details
                      </label>
                      <input className="card-input" type="text" placeholder="Card number" disabled={signedIn !== true} />
                    </div>
                    <div className="card-row">
                      <input className="card-input" type="text" placeholder="MM / YY" disabled={signedIn !== true} />
                      <input className="card-input" type="text" placeholder="CVC" disabled={signedIn !== true} />
                    </div>
                    <div className="card-secure-note">
                      <Icon>
                        <rect x="3" y="11" width="18" height="11" rx="2" />
                        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                      </Icon>
                      Card details are collected on the secure payment page after you continue.
                    </div>
                  </div>
                ) : (
                  <div
                    style={{
                      marginTop: 14,
                      background: 'var(--sky-2)',
                      border: '1px solid var(--line-2)',
                      borderRadius: 12,
                      padding: '14px 16px',
                      fontSize: '13.5px',
                      color: 'var(--body)',
                      fontWeight: 600,
                    }}
                  >
                    You will be redirected to HyperPay to complete payment securely.
                  </div>
                )}
              </div>
            </div>

            <div className="form-card">
              <div className="fc-section">
                <div className="fc-sec-head">
                  <div className="fc-sec-num">3</div>
                  <div className="fc-sec-title">Confirmation</div>
                </div>
                <div className="cb-row">
                  <input
                    id="cbTerms"
                    type="checkbox"
                    checked={termsOk}
                    onChange={(e) => setTermsOk(e.target.checked)}
                    disabled={signedIn !== true}
                  />
                  <label htmlFor="cbTerms">
                    I agree to the{' '}
                    <Link to="/terms" target="_blank" rel="noopener noreferrer">
                      Terms &amp; Conditions
                    </Link>
                  </label>
                </div>
                {checkboxErrors.terms ? (
                  <span className="cb-err visible">Please agree to the Terms &amp; Conditions.</span>
                ) : null}
                <div className="cb-row">
                  <input
                    id="cbPrivacy"
                    type="checkbox"
                    checked={privacyOk}
                    onChange={(e) => setPrivacyOk(e.target.checked)}
                    disabled={signedIn !== true}
                  />
                  <label htmlFor="cbPrivacy">
                    I agree to the{' '}
                    <Link to="/privacy" target="_blank" rel="noopener noreferrer">
                      Privacy Policy
                    </Link>
                  </label>
                </div>
                {checkboxErrors.privacy ? (
                  <span className="cb-err visible">Please agree to the Privacy Policy.</span>
                ) : null}
                <div className="cb-row">
                  <input
                    id="cbRefund"
                    type="checkbox"
                    checked={refundOk}
                    onChange={(e) => setRefundOk(e.target.checked)}
                    disabled={signedIn !== true}
                  />
                  <label htmlFor="cbRefund">
                    I have read and understand the{' '}
                    <Link to="/refund" target="_blank" rel="noopener noreferrer">
                      Refund Policy
                    </Link>
                  </label>
                </div>
                {checkboxErrors.refund ? (
                  <span className="cb-err visible">Please confirm you have read the Refund Policy.</span>
                ) : null}
                {submitError || alreadyOwned ? (
                  <div className="form-err visible" role="alert">
                    <Icon>
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="12" />
                      <line x1="12" y1="16" x2="12.01" y2="16" />
                    </Icon>
                    <span>
                      {alreadyOwned
                        ? `You already have access to ${productLabel}. No additional purchase is needed — visit your Dashboard to continue learning.`
                        : submitError}
                    </span>
                  </div>
                ) : null}
              </div>
            </div>
          </div>

          <div>
            <div className="order-summary">
              <div className="os-title">Order Summary</div>
              <div className="os-product">{productLabel}</div>
              <div className="os-product-sub">
                {isBundle ? 'All 4 courses included' : `${productLabel} · 1 course`}
              </div>
              {loadError ? (
                <p style={{ color: '#b91c1c', fontWeight: 600 }} role="alert">
                  {loadError}
                </p>
              ) : (
                <>
                  <div className="os-price-rows">
                    <div className="os-pr">
                      <span>{isBundle ? 'Bundle Price' : 'Course Price'}</span>
                      <span>{origLabel && isBundle ? origLabel : priceLabel ?? '…'}</span>
                    </div>
                    {discountLabel && isBundle ? (
                      <div className="os-pr discount">
                        <span>Bundle Discount</span>
                        <span>-{discountLabel}</span>
                      </div>
                    ) : null}
                  </div>
                  <div className="os-total">
                    <span className="os-total-lbl">Total</span>
                    <span className="os-total-price">{priceLabel ?? '…'}</span>
                  </div>
                  <div className="os-includes">
                    <div className="os-inc-title">Included</div>
                    {includesCourses.map((title) => (
                      <div key={title} className="os-inc-item">
                        <CheckIcon strokeWidth="2.5" />
                        {title}
                      </div>
                    ))}
                    <div className="os-inc-item">
                      <CheckIcon strokeWidth="2.5" />
                      Lifetime Access
                    </div>
                    <div className="os-inc-item">
                      <CheckIcon strokeWidth="2.5" />
                      Competency-Based Certificate{includesCourses.length > 1 ? 's' : ''} of Completion
                    </div>
                  </div>
                </>
              )}
              {signedIn === true ? (
                <button
                  type="button"
                  className="btn btn-primary os-btn"
                  data-testid="checkout-submit"
                  disabled={submitting || Boolean(loadError) || alreadyOwned}
                  onClick={() => void onSubmit()}
                >
                  <span>{submitLabel}</span>
                  <div className={`btn-spinner${submitting ? ' v' : ''}`} />
                  {!submitting ? <ArrowIcon /> : null}
                </button>
              ) : null}
              <div className="os-secure">
                <Icon>
                  <rect x="3" y="11" width="18" height="11" rx="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </Icon>
                Secure · Encrypted · Trusted
              </div>
              <div
                style={{
                  marginTop: 14,
                  paddingTop: 14,
                  borderTop: '1px solid var(--line-2)',
                  fontSize: '12.5px',
                  fontWeight: 700,
                  color: 'var(--muted)',
                }}
              >
                <div style={{ marginBottom: 8 }}>Accepted: Visa, Mastercard, American Express, HyperPay</div>
                <div style={{ marginBottom: 8 }}>
                  Your certificate will be issued with a unique credential ID that employers and institutions can verify
                  online.
                </div>
                <div style={{ marginBottom: 8 }}>
                  All purchases are final per our{' '}
                  <Link to="/refund" style={{ color: 'var(--blue)' }}>
                    Refund Policy
                  </Link>{' '}
                  — access begins immediately upon payment.
                </div>
                <div>
                  Completing all 4 courses (incl. via this Bundle) makes you eligible to apply for the{' '}
                  <Link to="/research-team" style={{ color: 'var(--blue)' }}>
                    Research Team
                  </Link>
                  .
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <section className="co-trust-strip">
        <div className="wrap">
          <p className="kicker" style={{ marginBottom: 20, textAlign: 'center' }}>
            Why Learners Trust Research Spectrum
          </p>
          <div className="co-trust-inner reveal">
            {[
              'Created by a published physician-researcher',
              'Competency-based Certificate of Completion pathway',
              'Public certificate verification with unique credential ID',
              'Lifetime access — no subscription, no recurring fees',
              'Practical project-based learning with expert feedback',
              'Research Team pathway — contribute to published studies',
            ].map((item) => (
              <div key={item} className="co-trust-item">
                <span className="co-trust-ck">
                  <CheckIcon />
                </span>
                {item}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="sec" style={{ padding: '48px 0', background: 'var(--sky-2)', borderTop: '1px solid var(--line-2)', borderBottom: '1px solid var(--line-2)' }}>
        <div className="wrap">
          <div className="instructor-card reveal">
            <img className="ic-photo" src={instructorPhoto} alt="Dr. Bahaa Aburayya" loading="lazy" />
            <div className="ic-body">
              <div className="ic-name">Dr. Bahaa Aburayya, MD</div>
              <div className="ic-title">Postdoctoral Research Fellow</div>
              <div className="ic-affil">
                <div className="ic-affil-item">
                  <b>Department of Surgery — Division of Cardiothoracic Surgery</b>
                  <br />
                  Mayo Clinic Arizona
                </div>
                <div className="ic-affil-item" style={{ marginTop: 4 }}>
                  <b>Department of Surgery — Division of Surgical Oncology</b>
                  <br />
                  University of California, San Francisco (UCSF) — Remote Research Collaborator
                </div>
              </div>
              <div className="ic-bio">
                Published researcher with peer-reviewed publications and presentations at national and international
                conferences.
              </div>
              <Link to="/about" className="ic-cta">
                View Instructor Profile <ArrowIcon />
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="sec" style={{ background: 'var(--sky-2)', borderTop: '1px solid var(--line-2)', borderBottom: '1px solid var(--line-2)' }}>
        <div className="wrap">
          <div style={{ textAlign: 'center', marginBottom: 40 }} className="reveal">
            <p className="kicker">Choose Your Path</p>
            <h2 className="title">Individual Course vs. Research Mastery Bundle</h2>
          </div>
          <div className="comparison-table reveal" style={{ maxWidth: 820, margin: '0 auto' }}>
            <div className="ct-head">
              <div className="ct-head-cell">Feature</div>
              <div className="ct-head-cell">
                Individual Course
                <br />
                <span style={{ fontSize: 17, fontWeight: 800, color: 'var(--blue)' }}>
                  {dollars(orderedCourses[0]?.amountMinor) ?? '$50'}
                </span>
              </div>
              <div className="ct-head-cell featured">
                Research Mastery Bundle
                <br />
                <span style={{ fontSize: 17, fontWeight: 800 }}>
                  {dollars(bundleAmountMinor) ?? '$150'}{' '}
                  {origLabel ? (
                    <span style={{ fontSize: 12, opacity: 0.85, textDecoration: 'line-through' }}>{origLabel}</span>
                  ) : null}
                </span>
              </div>
            </div>
            {[
              ['Course modules + quizzes', true, true],
              ['Final assignment + feedback', true, true],
              ['Certificate of Completion', true, true],
              ['Lifetime access', true, true],
              ['All 4 courses', false, true],
              ['Research Team eligibility', 'requires', true],
              ['Bundle savings', false, 'save'],
            ].map(([feature, single, bundle]) => (
              <div key={String(feature)} className="ct-row">
                <div className="ct-cell">{feature}</div>
                <div className={`ct-cell${single === true ? ' check' : single === 'requires' ? '' : ' cross'}`}>
                  {single === true ? (
                    <CheckIcon strokeWidth="2.5" />
                  ) : single === 'requires' ? (
                    <span style={{ fontSize: 12, color: 'var(--muted)' }}>Requires all 4</span>
                  ) : (
                    <Icon strokeWidth="2.5">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </Icon>
                  )}
                </div>
                <div className={`ct-cell${bundle === true ? ' check' : bundle === 'save' ? '' : ' cross'}`}>
                  {bundle === true ? (
                    <CheckIcon strokeWidth="2.5" />
                  ) : bundle === 'save' ? (
                    <span style={{ fontWeight: 800, color: '#0d6f3e', fontSize: 14 }}>
                      {discountLabel ? `${discountLabel} saved` : '$50 saved'}
                    </span>
                  ) : (
                    <Icon strokeWidth="2.5">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </Icon>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="sec" style={{ background: 'var(--sky-2)', borderTop: '1px solid var(--line-2)', borderBottom: '1px solid var(--line-2)' }}>
        <div className="wrap">
          <div style={{ textAlign: 'center', marginBottom: 40 }} className="reveal">
            <p className="kicker">For Organizations</p>
            <h2 className="title">Need Access For Multiple Learners?</h2>
            <p className="lead" style={{ marginTop: 12 }}>
              Research Spectrum supports group access for hospitals, universities, and research departments — with
              simplified billing and onboarding for your team.
            </p>
          </div>
          <div className="included-grid">
            {[
              ['University Partnerships', 'Provide structured research training to medical students and faculty as part of your curriculum.'],
              ['Hospital Training Programs', 'Equip residents and fellows with practical research methodology and statistics skills.'],
              ['Department Licensing', 'License access for an entire department or research unit under a single agreement.'],
              ['Bulk Enrollment', 'Enroll groups of learners at once with volume-based pricing for institutional access.'],
            ].map(([title, body], index) => (
              <div key={title} className="inc-card reveal" data-d={String((index % 4) + 1)}>
                <div className="inc-ic">
                  <Icon>
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                    <circle cx="9" cy="7" r="4" />
                  </Icon>
                </div>
                <h3>{title}</h3>
                <p>{body}</p>
              </div>
            ))}
          </div>
          <div style={{ textAlign: 'center', marginTop: 36 }} className="reveal">
            <a href="mailto:sales@researchspectrum.org" className="btn btn-primary">
              Contact Sales
              <ArrowIcon />
            </a>
            <Link to="/contact" className="btn btn-ghost" style={{ marginLeft: 12 }}>
              Partnership Inquiry Form
            </Link>
          </div>
        </div>
      </section>

      <section className="sec" style={{ background: 'var(--sky-2)', borderTop: '1px solid var(--line-2)' }}>
        <div className="wrap">
          <div style={{ textAlign: 'center', marginBottom: 40 }} className="reveal">
            <p className="kicker">Questions</p>
            <h2 className="title">Frequently Asked Questions</h2>
          </div>
          <div className="rt-faq-list reveal">
            {CHECKOUT_FAQ.map((item, index) => {
              const open = openFaq === index
              return (
                <div key={item.q} className={`rt-faq-item${open ? ' open' : ''}`}>
                  <button
                    type="button"
                    className="rt-faq-q"
                    aria-expanded={open}
                    onClick={() => setOpenFaq(open ? null : index)}
                  >
                    <h3>{item.q}</h3>
                    <div className="rt-faq-ic">
                      <Icon strokeWidth="2.5">
                        <line x1="12" y1="5" x2="12" y2="19" />
                        <line x1="5" y1="12" x2="19" y2="12" />
                      </Icon>
                    </div>
                  </button>
                  <div className="rt-faq-a">
                    <p>{item.a}</p>
                  </div>
                </div>
              )
            })}
          </div>
          <div style={{ textAlign: 'center', marginTop: 28 }} className="reveal">
            <Link to="/faq" style={{ fontSize: 14, fontWeight: 700, color: 'var(--blue)' }}>
              View all frequently asked questions →
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
