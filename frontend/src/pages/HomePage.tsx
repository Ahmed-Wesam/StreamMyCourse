import { useEffect, useRef, useState, type RefObject } from 'react'
import { Link } from 'react-router-dom'

import { listPublishedCourses } from '../lib/api/public-catalog'
import { usePageTitle } from '../lib/page-title'
import './HomePage.css'

function useCourseHrefs(): (title: string) => string {
  const [hrefs, setHrefs] = useState<Record<string, string>>({})

  useEffect(() => {
    let cancelled = false
    void listPublishedCourses()
      .then((courses) => {
        if (cancelled) return
        const next: Record<string, string> = {}
        for (const course of courses) {
          next[course.title] = `/courses/${course.id}`
        }
        setHrefs(next)
      })
      .catch(() => {
        /* Static cards stay linked to the catalog when the list is unavailable. */
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (title: string) => hrefs[title] ?? '/courses'
}

function useReveal(rootRef: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const root = rootRef.current
    if (!root) return
    const nodes = Array.from(root.querySelectorAll('.reveal'))
    if (typeof IntersectionObserver === 'undefined') {
      for (const el of nodes) el.classList.add('in')
      return
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue
          entry.target.classList.add('in')
          observer.unobserve(entry.target)
        }
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' },
    )
    for (const el of nodes) observer.observe(el)
    return () => observer.disconnect()
  }, [rootRef])
}

export default function HomePage() {
  usePageTitle()
  const rootRef = useRef<HTMLDivElement>(null)
  const courseHref = useCourseHrefs()
  useReveal(rootRef)

  return (
    <div ref={rootRef} className="pg-home" data-testid="student-page-home">
      <section className="hero">
        <div className="wrap hero-grid">
          <div className="hero-copy">
            <span className="eyebrow anim a1"><span className="dot"></span> Research · Analyze · Publish</span>
            <h1 className="anim a2">Master Medical Research. Analyze Data. <span className="g">Publish With Confidence.</span></h1>
            <p className="sub anim a3">Comprehensive online training in research methodology, statistics, scientific writing, and systematic reviews — designed specifically for healthcare professionals.</p>
            <div className="hero-ctas anim a4">
              <Link to="/courses#courses-catalog" className="btn btn-primary">Explore Courses
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
              </Link>
              <a href="#courses" className="btn btn-ghost">Learn More</a>
            </div>
            <div className="hero-auth anim a5">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
              Built by an active medical researcher — for healthcare professionals.
            </div>
          </div>

          <div className="hero-visual">
            <svg className="laptop" viewBox="0 0 430 300" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="scr" x1="0" y1="0" x2="430" y2="270"><stop stopColor="#f6f9ff"/><stop offset="1" stopColor="#eaf1ff"/></linearGradient>
                <linearGradient id="bg1" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#1e5eff"/><stop offset="1" stopColor="#3a86ff"/></linearGradient>
                <linearGradient id="bg2" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#0d1c40"/><stop offset="1" stopColor="#1b48c9"/></linearGradient>
              </defs>
              <rect x="35" y="14" width="360" height="232" rx="14" fill="#0d1c40"/>
              <rect x="44" y="22" width="342" height="216" rx="8" fill="url(#scr)"/>
              <rect x="58" y="36" width="120" height="11" rx="5.5" fill="#0d1c40"/>
              <rect x="58" y="53" width="80" height="7" rx="3.5" fill="#b9c8ea"/>
              <rect x="300" y="34" width="70" height="22" rx="11" fill="url(#bg1)"/>
              <rect x="58" y="74" width="96" height="44" rx="9" fill="#fff" stroke="#e2ebff"/><rect x="68" y="84" width="40" height="9" rx="4" fill="#1e5eff"/><rect x="68" y="100" width="60" height="6" rx="3" fill="#c7d6f6"/>
              <rect x="166" y="74" width="96" height="44" rx="9" fill="#fff" stroke="#e2ebff"/><rect x="176" y="84" width="34" height="9" rx="4" fill="#0d1c40"/><rect x="176" y="100" width="64" height="6" rx="3" fill="#c7d6f6"/>
              <rect x="274" y="74" width="96" height="44" rx="9" fill="#fff" stroke="#e2ebff"/><rect x="284" y="84" width="44" height="9" rx="4" fill="#22c55e"/><rect x="284" y="100" width="52" height="6" rx="3" fill="#c7d6f6"/>
              <rect x="58" y="130" width="200" height="96" rx="10" fill="#fff" stroke="#e2ebff"/><rect x="70" y="142" width="60" height="7" rx="3.5" fill="#0d1c40"/>
              <rect x="74" y="200" width="16" height="14" rx="3" fill="#bcd0f7"/><rect x="100" y="186" width="16" height="28" rx="3" fill="#7fa8f5"/><rect x="126" y="170" width="16" height="44" rx="3" fill="url(#bg1)"/><rect x="152" y="190" width="16" height="24" rx="3" fill="#7fa8f5"/><rect x="178" y="162" width="16" height="52" rx="3" fill="url(#bg2)"/><rect x="204" y="180" width="16" height="34" rx="3" fill="#bcd0f7"/>
              <rect x="266" y="130" width="104" height="96" rx="10" fill="#fff" stroke="#e2ebff"/>
              <circle cx="318" cy="180" r="30" fill="none" stroke="#e2ebff" strokeWidth="11"/>
              <circle cx="318" cy="180" r="30" fill="none" stroke="url(#bg1)" strokeWidth="11" strokeDasharray="120 188" strokeLinecap="round" transform="rotate(-90 318 180)"/>
              <circle cx="318" cy="180" r="30" fill="none" stroke="#0d1c40" strokeWidth="11" strokeDasharray="44 188" strokeDashoffset="-122" strokeLinecap="round" transform="rotate(-90 318 180)"/>
              <path d="M18 246h394l16 18H2z" fill="#c3d0ec"/><rect x="186" y="250" width="58" height="6" rx="3" fill="#9fb3da"/>
            </svg>
            <div className="books">
              <div className="book b1">Methodology</div><div className="book b2">Statistics</div><div className="book b3">Writing</div><div className="book b4">Systematic Reviews</div>
            </div>
            <div className="float-card fc-1">
              <div className="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"/><path d="M7 14l4-4 3 3 5-6"/></svg></div>
              <div><small>SPSS Analysis</small><strong>ANOVA · Regression · Chi-Square</strong></div>
            </div>
            <div className="float-card fc-2">
              <div className="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5"/></svg></div>
              <div><small>Manuscript</small><strong>Publication Ready</strong></div>
            </div>
            <div className="float-card fc-3">
              <div className="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="6"/><path d="M9 13.8 7 22l5-3 5 3-2-8.2"/></svg></div>
              <div><small>Certificate</small><strong>Competency Verified</strong></div>
            </div>
          </div>
        </div>
      </section>


      <section className="trust">
        <div className="wrap">
          <div className="trust-card reveal">
            <div className="trust-item">
              <div className="ti"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg></div>
              <span>Beginner Friendly</span>
            </div>
            <div className="trust-item">
              <div className="ti"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94z"/></svg></div>
              <span>Practical & Applied</span>
            </div>
            <div className="trust-item">
              <div className="ti"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg></div>
              <span>Lifetime Access</span>
            </div>
            <div className="trust-item">
              <div className="ti"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="6"/><path d="M9 13.8 7 22l5-3 5 3-2-8.2"/></svg></div>
              <span>Certificate of Completion</span>
            </div>
            <div className="trust-item">
              <div className="ti"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg></div>
              <span>Research Team Pathway</span>
            </div>
          </div>
        </div>
      </section>


      <section className="sec">
        <div className="wrap">
          <div className="sec-head sec-head-lg">
            <span className="kicker reveal">Outcomes</span>
            <h2 className="title reveal" data-d="1">What You'll Be Able To Do</h2>
            <p className="lead reveal" data-d="2">Master practical research skills you can immediately apply to your own projects.</p>
          </div>
          <div className="out-grid">
            <article className="out-card reveal" data-d="1">
              <div className="oi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6M9 16h4"/></svg></div>
              <h3>Conduct Your Own Study</h3>
              <p>Move from a research question to a complete, well-designed study you can actually run.</p>
            </article>
            <article className="out-card reveal" data-d="2">
              <div className="oi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"/><rect x="7" y="13" width="3" height="5" rx="1"/><rect x="12" y="9" width="3" height="9" rx="1"/><rect x="17" y="5" width="3" height="13" rx="1"/></svg></div>
              <h3>Analyze Data Using SPSS</h3>
              <p>Clean, manage, analyze, and interpret your datasets using SPSS with confidence and methodological rigor.</p>
            </article>
            <article className="out-card reveal" data-d="3">
              <div className="oi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg></div>
              <h3>Write Your Own Manuscript</h3>
              <p>Structure every section of a scientific paper — from introduction to discussion.</p>
            </article>
            <article className="out-card reveal" data-d="1">
              <div className="oi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg></div>
              <h3>Conduct Systematic Reviews & Meta-Analyses</h3>
              <p>Search, screen, extract, and synthesize evidence into a publishable review.</p>
            </article>
            <article className="out-card reveal" data-d="2">
              <div className="oi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg></div>
              <h3>Publish Your Research</h3>
              <p>Choose the right journal, submit correctly, and navigate the peer-review process.</p>
            </article>
          </div>
        </div>
      </section>


      <section className="sec journey">
        <div className="wrap">
          <div className="sec-head sec-head-lg">
            <span className="kicker reveal">The Path</span>
            <h2 className="title reveal" data-d="1">Your Research Journey Starts Here</h2>
            <p className="lead reveal" data-d="2">A structured learning path designed to take you from beginner to independent researcher.</p>
          </div>
          <div className="road reveal" data-d="1">
            <div className="step">
              <div className="node"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/></svg></div>
              <span className="num">STEP 01</span><h4>Research Methodology</h4>
            </div>
            <div className="step">
              <div className="node"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"/><rect x="7" y="13" width="3" height="5" rx="1"/><rect x="12" y="9" width="3" height="9" rx="1"/><rect x="17" y="5" width="3" height="13" rx="1"/></svg></div>
              <span className="num">STEP 02</span><h4>Statistics & SPSS</h4>
            </div>
            <div className="step">
              <div className="node"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg></div>
              <span className="num">STEP 03</span><h4>Scientific Writing</h4>
            </div>
            <div className="step">
              <div className="node"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg></div>
              <span className="num">STEP 04</span><h4>Systematic Reviews & Meta-Analysis</h4>
            </div>
            <div className="step final">
              <div className="node"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg></div>
              <span className="num">GOAL</span><h4>Research Team Eligibility</h4>
            </div>
          </div>
        </div>
      </section>


      <section className="sec" id="courses">
        <div className="wrap">
          <div className="sec-head sec-head-xl">
            <span className="kicker reveal">Our Courses</span>
            <h2 className="title reveal" data-d="1">Four Courses. One Complete Research Skill Set.</h2>
            <p className="lead reveal" data-d="2">Take them individually, or get everything with the Research Mastery Bundle.</p>
          </div>

          <div className="course-grid">
            <article className="course-card reveal" data-d="1">
              <div className="cico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6M9 16h4"/></svg></div>
              <div className="cbody">
                <h3>Research Methodology</h3>
                <ul>
                  <li>Formulate research questions</li>
                  <li>Design robust studies</li>
                  <li>Develop protocols</li>
                  <li>Build publishable projects</li>
                </ul>
                <div className="course-foot">
                  <div className="price">$50 <small>one-time payment</small></div>
                  <Link to={courseHref("Research Methodology")} className="mini-btn">View Course <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></Link>
                </div>
              </div>
            </article>

            <article className="course-card reveal" data-d="2">
              <div className="cico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"/><rect x="7" y="13" width="3" height="5" rx="1"/><rect x="12" y="9" width="3" height="9" rx="1"/><rect x="17" y="5" width="3" height="13" rx="1"/></svg></div>
              <div className="cbody">
                <h3>Statistics & SPSS</h3>
                <ul>
                  <li>Run ANOVA, Chi-Square, Regression & Logistic Regression</li>
                  <li>Perform Survival Analysis in SPSS</li>
                  <li>Interpret SPSS output with confidence</li>
                  <li>Write publishable Methods & Results sections</li>
                </ul>
                <div className="course-foot">
                  <div className="price">$50 <small>one-time payment</small></div>
                  <Link to={courseHref("Statistics & SPSS")} className="mini-btn">View Course <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></Link>
                </div>
              </div>
            </article>

            <article className="course-card reveal" data-d="3">
              <div className="cico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg></div>
              <div className="cbody">
                <h3>Scientific Writing</h3>
                <ul>
                  <li>Structure scientific manuscripts</li>
                  <li>Write every section effectively</li>
                  <li>Avoid common writing mistakes</li>
                  <li>Prepare papers for submission</li>
                </ul>
                <div className="course-foot">
                  <div className="price">$50 <small>one-time payment</small></div>
                  <Link to={courseHref("Scientific Writing")} className="mini-btn">View Course <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></Link>
                </div>
              </div>
            </article>

            <article className="course-card reveal" data-d="4">
              <div className="cico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg></div>
              <div className="cbody">
                <h3>Systematic Reviews & Meta-Analysis</h3>
                <ul>
                  <li>Conduct systematic searches</li>
                  <li>Screen studies efficiently</li>
                  <li>Extract and analyze data</li>
                  <li>Produce publishable reviews</li>
                </ul>
                <div className="course-foot">
                  <div className="price">$50 <small>one-time payment</small></div>
                  <Link to={courseHref("Systematic Reviews & Meta-Analysis")} className="mini-btn">View Course <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></Link>
                </div>
              </div>
            </article>
          </div>


          <div className="bundle reveal" data-d="1">
            <div className="bl">
              <span className="best-tag"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l2.4 7.4H22l-6 4.4 2.3 7.2L12 16.6 5.7 21l2.3-7.2-6-4.4h7.6z"/></svg> Best Value</span>
              <h3>Research Mastery Bundle</h3>
              <p>A complete research pathway — design your study, analyze data in SPSS, write and submit your manuscript, and conduct a systematic review. Everything you need from first concept to published paper, in one program.</p>
              <div className="incl">
                <span>Research Methodology</span><span>Statistics & SPSS</span><span>Scientific Writing</span><span>Systematic Reviews & Meta-Analysis</span>
              </div>
            </div>
            <div className="br">
              <div className="bprice"><span>$150</span><small>one-time payment</small></div>
              <div className="save">Save $50 vs. buying separately</div>
              <Link to="/checkout?productType=bundle" className="btn btn-white">Enroll in Bundle
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
              </Link>
            </div>
          </div>

          <div className="courses-more reveal">
            <Link to="/courses#courses-catalog" className="btn btn-ghost">Explore Courses
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
            </Link>
          </div>
        </div>
      </section>


      <section className="sec beyond">
        <div className="wrap">
          <div className="sec-head">
            <span className="kicker reveal">The Opportunity</span>
            <h2 className="title reveal" data-d="1">Beyond The Courses</h2>
            <p className="lead reveal" data-d="2">Research Spectrum is more than an educational platform.</p>
          </div>

          <div className="timeline">
            <div className="tl-step reveal" data-d="1">
              <div className="tnode"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg></div>
              <div className="tl-body"><div className="tn">Step 01</div><h4>Complete All Four Courses</h4><p>Build the full research skill set across methodology, statistics, writing, and reviews.</p></div>
            </div>
            <div className="tl-step reveal" data-d="1">
              <div className="tnode"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="6"/><path d="M9 13.8 7 22l5-3 5 3-2-8.2"/></svg></div>
              <div className="tl-body"><div className="tn">Step 02</div><h4>Earn Certificates</h4><p>Receive a Certificate of Completion for each course you finish.</p></div>
            </div>
            <div className="tl-step reveal" data-d="1">
              <div className="tnode"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M9 15l2 2 4-4"/></svg></div>
              <div className="tl-body"><div className="tn">Step 03</div><h4>Apply To The Research Team</h4><p>Become eligible to apply for the Research Spectrum Research Team.</p></div>
            </div>
            <div className="tl-step reveal" data-d="1">
              <div className="tnode"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="m17 11 2 2 4-4"/></svg></div>
              <div className="tl-body"><div className="tn">Step 04</div><h4>Interview & Selection Process</h4><p>Selected applicants move through interviews and a structured review.</p></div>
            </div>
            <div className="tl-step reveal" data-d="1">
              <div className="tnode"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z"/><path d="M2 21a7 7 0 0 1 14 0"/><path d="M19 8v6M16 11h6"/></svg></div>
              <div className="tl-body"><div className="tn">Step 05</div><h4>Participate In Real Research Projects</h4><p>Contribute to genuine, ongoing research alongside the team.</p></div>
            </div>
            <div className="tl-step peak reveal" data-d="1">
              <div className="tnode"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M6 2h9l5 5v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z"/><path d="M14 2v5h5M9 13h6M9 17h4"/></svg></div>
              <div className="tl-body"><div className="tn">The Goal</div><h4>Potential Authorship & Publications</h4><p>Earn the opportunity for authorship on published research.</p></div>
            </div>
          </div>

          <div className="eligibility reveal" data-d="2">
            <h5><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg> How Eligibility Works</h5>
            <div className="elig-item"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5"/></svg> Students who complete all four courses become eligible to apply for the Research Spectrum Research Team.</div>
            <div className="elig-item"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5"/></svg> Selection is based on interviews, course performance, assignments, English proficiency, and research skills.</div>
            <div className="elig-item elig-note"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 8h.01M12 12v4"/></svg> Eligibility does not guarantee acceptance.</div>
          </div>
        </div>
      </section>


      <section className="sec">
        <div className="wrap">
          <div className="sec-head">
            <span className="kicker reveal">The Platform</span>
            <h2 className="title reveal" data-d="1">Why Research Spectrum</h2>
            <p className="lead reveal" data-d="2">Everything you need to become an independent researcher.</p>
          </div>
          <div className="who-grid">
            <div className="feat reveal" data-d="1">
              <div className="fic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6M9 16h4"/></svg></div>
              <h3>Real Research Datasets</h3>
              <p>Work with realistic datasets and practical examples that mirror real-world healthcare research.</p>
            </div>
            <div className="feat reveal" data-d="2">
              <div className="fic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"/><rect x="7" y="13" width="3" height="5" rx="1"/><rect x="12" y="9" width="3" height="9" rx="1"/><rect x="17" y="5" width="3" height="13" rx="1"/></svg></div>
              <h3>SPSS Training Included</h3>
              <p>Learn how to clean data, select statistical tests, analyze results, and interpret SPSS output.</p>
            </div>
            <div className="feat reveal" data-d="3">
              <div className="fic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="6"/><path d="M9 13.8 7 22l5-3 5 3-2-8.2"/></svg></div>
              <h3>Certificate-Based Assessment</h3>
              <p>Earn certificates by successfully completing quizzes, assignments, and competency-based evaluations.</p>
            </div>
            <div className="feat reveal" data-d="4">
              <div className="fic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg></div>
              <h3>Healthcare-Focused Curriculum</h3>
              <p>Designed specifically for medical students, residents, researchers, and healthcare professionals.</p>
            </div>
            <div className="feat reveal" data-d="5">
              <div className="fic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="m17 11 2 2 4-4"/></svg></div>
              <h3>Practical Assignments</h3>
              <p>Apply each concept through hands-on assignments designed to build real, usable research skills.</p>
            </div>
          </div>
        </div>
      </section>


      <section className="sec">
        <div className="wrap">
          <div className="sec-head">
            <span className="kicker reveal">FAQ</span>
            <h2 className="title reveal" data-d="1">Frequently Asked Questions</h2>
            <p className="lead reveal" data-d="2">Common questions from future students.</p>
          </div>

          <div className="faq-list reveal" data-d="1">
            <div className="faq-item">
              <div className="faq-q">Do I need prior research experience?</div>
              <div className="faq-a">No. The courses are designed to take learners from beginner level to independent research capability. You'll start with core concepts and progress through each skill systematically — no prior experience is assumed.</div>
            </div>
            <div className="faq-item">
              <div className="faq-q">Do I need statistics knowledge before starting?</div>
              <div className="faq-a">No. The Statistics & SPSS course starts with fundamental concepts before progressing to analyses including Chi-Square, ANOVA, Regression, Logistic Regression, Survival Analysis, and SPSS output interpretation. All statistical work is done inside SPSS with guided instruction.</div>
            </div>
            <div className="faq-item">
              <div className="faq-q">Is SPSS included in the training?</div>
              <div className="faq-a">Yes. The Statistics & SPSS course includes extensive hands-on SPSS instruction — you'll learn to enter and clean data, run the full range of statistical tests, and correctly interpret your SPSS output for inclusion in manuscripts.</div>
            </div>
            <div className="faq-item">
              <div className="faq-q">How long do I have access?</div>
              <div className="faq-a">You receive lifetime access to every course you purchase. There are no subscriptions, no recurring fees — pay once and return to your material for as long as the course remains available.</div>
            </div>
          </div>
          <div className="courses-more reveal">
            <Link to="/faq" className="btn btn-ghost">View All FAQs
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
            </Link>
          </div>
        </div>
      </section>


      <section className="cta-band">
        <div className="wrap">
          <div className="cta-inner reveal">
            <h2>Become an Independent Researcher</h2>
            <p>Learn the exact skills needed to design studies, analyze data, write manuscripts, and publish research with confidence.</p>
            <div className="btn-w">
              <Link to="/courses#courses-catalog" className="btn btn-white">Explore Courses
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
              </Link>
              <a href="#courses" className="btn btn-outline-w">Learn More</a>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
