import { useEffect, useLayoutEffect, useMemo, useRef, useState, type CSSProperties, type RefObject } from 'react'
import { Link } from 'react-router-dom'

import type { Course, CourseModule, CourseProgress, Lesson } from '../../lib/api/types'
import {
  DEFAULT_SECTION_HEADINGS,
  effectiveSectionHeading,
  sectionHasText,
  type CoursePageDocument,
  type CoursePageTextCard,
} from '../../lib/course-page'
import { formatJodMinor } from '../../lib/formatJodMinor'
import { isHttpsUrl } from '../../lib/isHttpsUrl'
import { groupLessonsByModule, type LessonModuleSection } from '../../lib/lessonGrouping'
import { courseDetailNoAccessPrompt } from '../../lib/marketing/courseDetailShellCopy'
import { isModuleLocked, hasNavigableModuleQuiz } from '../../lib/moduleGating'
import { lessonPlayerPath, moduleQuizLinkTo } from '../../lib/moduleQuizNavigation'
import { buildContinueHref, resolveContinueTarget } from '../../lib/studentDashboard'
import { CourseDetailHeroVisual } from './CourseDetailHeroVisual'
import {
  Arrow,
  ChartIcon,
  CheckIcon,
  Chevron,
  ChevronDown,
  ClockIcon,
  CrossIcon,
  DollarIcon,
  HANDS_ON_GLYPHS,
  HIGHLIGHT_GLYPHS,
  JOURNEY_GLYPHS,
  LessonsIcon,
  MedalIcon,
  ModulesIcon,
  OwnGlyph,
  ShieldIcon,
  StarIcon,
} from './CourseDetailMarks'
import { lessonThumbnailProgressPercent } from './courseDetailProgress'
import { coursePageFromCourse } from './coursePageFromCourse'
import {
  CURRICULUM_NOTES,
  FEATURED_MODULES,
  JOURNEY,
  JOURNEY_STEPS,
  MODULE_DURATIONS,
  PROBLEM_CALLOUT_BODY,
  REJECTION_ITEMS,
  REVIEW_TOOLS,
  STUDY_DESIGNS,
  courseVisualKey,
  type CourseVisualKey,
} from './coursePrototype'

const EMPHASIS = [
  'when and why',
  'precision and reproducibility',
  'clear, persuasive, and publication-ready',
  'core concepts behind meta-analysis',
  'how every piece fits together into a complete, implementation-ready research project.',
  "you'll learn how to use them on realistic research datasets, with worked examples you can apply to your own projects immediately.",
  "it's communicating your results effectively in scientific manuscripts.",
  'from finished results all the way to a submitted, publication-ready manuscript.',
]

type CourseDetailViewProps = {
  course: Course
  courseId: string
  lessons: Lesson[]
  modules: CourseModule[]
  courseProgress: CourseProgress | null
  previewOnly: boolean
  needsAccess: boolean
  onToggleLessonComplete: (lesson: Lesson, nextCompleted: boolean) => void
  markingLessonId: string | null
}

function useReveal(rootRef: RefObject<HTMLElement | null>, readyKey: string) {
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
  }, [rootRef, readyKey])
}

function priceMinorOf(course: Course): number | undefined {
  const record = course as Course & { priceAmountMinor?: unknown; price_amount_minor?: unknown }
  const raw = course.amountMinor ?? record.priceAmountMinor ?? record.price_amount_minor
  return typeof raw === 'number' && Number.isFinite(raw) ? raw : undefined
}

function dollars(amountMinor: number | undefined): string | null {
  if (typeof amountMinor !== 'number' || !Number.isFinite(amountMinor) || amountMinor <= 0) return null
  return formatJodMinor(amountMinor)
}

function Emphasized({ text }: { text: string }) {
  for (const phrase of EMPHASIS) {
    const index = text.indexOf(phrase)
    if (index === -1) continue
    return (
      <>
        {text.slice(0, index)}
        <b>{phrase}</b>
        {text.slice(index + phrase.length)}
      </>
    )
  }
  const seventy = text.indexOf('70%')
  if (seventy === -1) return <>{text}</>
  return (
    <>
      {text.slice(0, seventy)}
      <b>70%</b>
      {text.slice(seventy + 3)}
    </>
  )
}

function SecHead({
  kicker,
  title,
  lead,
  headClass,
  titleClass,
  leadClass,
  titleStyle,
  leadStyle,
}: {
  kicker: string
  title: string
  lead?: string
  headClass?: string
  titleClass?: string
  leadClass?: string
  titleStyle?: CSSProperties
  leadStyle?: CSSProperties
}) {
  return (
    <div className={headClass ? `sec-head ${headClass}` : 'sec-head'}>
      <span className="kicker reveal">{kicker}</span>
      <h2 className={titleClass ? `title reveal ${titleClass}` : 'title reveal'} data-d="1" style={titleStyle}>
        {title}
      </h2>
      {lead ? (
        <p className={leadClass ? `lead reveal ${leadClass}` : 'lead reveal'} data-d="2" style={leadStyle}>
          {lead}
        </p>
      ) : null}
    </div>
  )
}

function countLabel(count: number, singular: string, plural: string) {
  return `${count} ${count === 1 ? singular : plural}`
}

function HeroTitle({ title, visual }: { title: string; visual: CourseVisualKey | null }) {
  if (visual === 'methodology') {
    return (
      <>
        Research <span className="g">Methodology</span>
      </>
    )
  }
  if (visual === 'statistics') {
    return (
      <>
        Statistics & <span className="g">SPSS</span>
      </>
    )
  }
  if (visual === 'writing') {
    return (
      <>
        Scientific <span className="g">Writing</span>
      </>
    )
  }
  if (visual === 'srma') {
    return (
      <>
        Systematic Reviews & <span className="g">Meta-Analysis</span>
      </>
    )
  }
  return <>{title}</>
}

function PrimaryAction({
  owned,
  courseId,
  lessons,
  modules,
  courseProgress,
}: {
  owned: boolean
  courseId: string
  lessons: Lesson[]
  modules: CourseModule[]
  courseProgress: CourseProgress | null
}) {
  if (!owned) {
    return (
      <a href="#enroll" className="btn btn-primary">
        Enroll Now <Arrow />
      </a>
    )
  }
  const progress = courseProgress ?? {
    courseId,
    totalReadyLessons: lessons.length,
    completedCount: 0,
    percentComplete: 0,
    lessons: [],
  }
  const target = resolveContinueTarget(lessons, modules, progress)
  const startTimeSec = target.kind === 'lesson' ? target.startTimeSec : 0
  const label = lessons.length === 0 ? 'No lessons' : startTimeSec > 0 ? 'Resume Learning' : 'Start Learning'
  if (lessons.length === 0 || target.kind === 'blocked') {
    return <span className="btn btn-primary cursor-not-allowed">{label}</span>
  }
  return (
    <Link to={buildContinueHref(courseId, target)} className="btn btn-primary">
      {label} <Arrow />
    </Link>
  )
}

function LessonLine({
  lesson,
  courseId,
  index,
  locked,
  linkDisabled,
  showActions,
  completed,
  marking,
  onToggle,
  progressPercent,
}: {
  lesson: Lesson
  courseId: string
  index: number
  locked: boolean
  linkDisabled: boolean
  showActions: boolean
  completed: boolean
  marking: boolean
  onToggle: (lesson: Lesson, nextCompleted: boolean) => void
  progressPercent: number | null
}) {
  const [menuOpen, setMenuOpen] = useState(false)
  const thumb = lesson.thumbnailUrl && isHttpsUrl(lesson.thumbnailUrl) ? lesson.thumbnailUrl : null
  const canOpen = !linkDisabled && !locked
  const title = canOpen ? (
    <Link to={`/courses/${courseId}/lessons/${lesson.id}`}>{lesson.title}</Link>
  ) : (
    lesson.title
  )

  return (
    <li>
      <span className="ix">{index + 1}</span>
      {thumb ? <img src={thumb} alt="" /> : null}
      {title}
      {progressPercent !== null ? (
        <div
          role="progressbar"
          aria-valuenow={progressPercent}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Lesson watched about ${progressPercent}%`}
          style={{ flexBasis: '100%', height: 3, background: 'var(--line-2)' }}
        >
          <div style={{ width: `${progressPercent}%`, height: '100%', background: 'var(--blue)' }} />
        </div>
      ) : null}
      {showActions ? (
        <span style={{ marginLeft: 'auto', position: 'relative' }}>
          <button
            type="button"
            aria-label={`Lesson actions: ${lesson.title}`}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <span aria-hidden>⋯</span>
          </button>
          {menuOpen ? (
            <span role="menu" aria-label={`Lesson menu: ${lesson.title}`}>
              <button
                type="button"
                role="menuitem"
                disabled={marking}
                onClick={() => {
                  onToggle(lesson, !completed)
                  setMenuOpen(false)
                }}
              >
                {marking ? 'Updating…' : completed ? 'Mark as incomplete' : 'Mark as complete'}
              </button>
            </span>
          ) : null}
        </span>
      ) : null}
    </li>
  )
}

function CurItem({
  index,
  section,
  open,
  onToggle,
  courseId,
  moduleRow,
  showQuiz,
  linkDisabled,
  showActions,
  courseProgress,
  markingLessonId,
  onToggleLessonComplete,
  featured,
  duration,
}: {
  index: number
  section: LessonModuleSection
  open: boolean
  onToggle: () => void
  courseId: string
  moduleRow: CourseModule | undefined
  showQuiz: boolean
  linkDisabled: boolean
  showActions: boolean
  courseProgress: CourseProgress | null
  markingLessonId: string | null
  onToggleLessonComplete: (lesson: Lesson, nextCompleted: boolean) => void
  featured: boolean
  duration: string | null
}) {
  const bodyRef = useRef<HTMLDivElement>(null)
  const moduleQuiz = moduleRow?.moduleQuiz
  const locked = isModuleLocked(moduleRow)
  const quizAvailable = showQuiz && moduleQuiz?.available === true
  const quizNavigable = quizAvailable && hasNavigableModuleQuiz(moduleRow)
  const quizReturnLesson = section.lessons[section.lessons.length - 1]
  const quizTo = quizNavigable
    ? moduleQuizLinkTo(
        courseId,
        section.id,
        quizReturnLesson ? lessonPlayerPath(courseId, quizReturnLesson.id) : `/courses/${courseId}`,
      )
    : null
  const note = section.description?.trim() ?? ''

  useLayoutEffect(() => {
    const body = bodyRef.current
    if (!body) return
    const fit = () => {
      body.style.maxHeight = open ? `${body.scrollHeight}px` : '0px'
    }
    fit()
    window.addEventListener('resize', fit)
    return () => window.removeEventListener('resize', fit)
  }, [open, section.lessons.length, note, quizTo])

  return (
    <div className={open ? 'cur-item open' : 'cur-item'}>
      <button type="button" className="cur-head" onClick={onToggle}>
        <span className="cur-num">{index + 1}</span>
        <span className="ct">
          <h3>
            {section.title}
            {featured ? (
              <span className="cur-badge">
                <StarIcon /> Featured Module
              </span>
            ) : null}
          </h3>
          <span className="sub">{countLabel(section.lessons.length, 'lesson', 'lessons')}</span>
          {quizAvailable ? <span className="sub">Module quiz</span> : null}
        </span>
        {duration ? <span className="cur-dur">{duration}</span> : null}
        <span className="cur-chev">
          <ChevronDown />
        </span>
      </button>
      <div className="cur-body" ref={bodyRef}>
        {quizAvailable && locked ? <p className="cur-note">Complete the prior module quiz to unlock</p> : null}
        {quizTo ? (
          <p className="cur-note">
            <Link to={quizTo.pathname} state={quizTo.state}>
              Start quiz
            </Link>
          </p>
        ) : null}
        {section.lessons.length > 0 ? (
          <ol>
            {section.lessons.map((lesson, lessonIndex) => {
              const progressItem = courseProgress?.lessons.find((item) => item.lessonId === lesson.id)
              return (
                <LessonLine
                  key={lesson.id}
                  lesson={lesson}
                  courseId={courseId}
                  index={lessonIndex}
                  locked={locked}
                  linkDisabled={linkDisabled}
                  showActions={showActions}
                  completed={progressItem?.completed ?? false}
                  marking={markingLessonId === lesson.id}
                  onToggle={onToggleLessonComplete}
                  progressPercent={lessonThumbnailProgressPercent(lesson, progressItem)}
                />
              )
            })}
          </ol>
        ) : null}
        {note ? (
          <p className="cur-note">
            <Emphasized text={note} />
          </p>
        ) : null}
      </div>
    </div>
  )
}

function ProblemCallout({
  title,
  body,
  fallbackBody,
  bodyClass,
}: {
  title?: string
  body?: string
  fallbackBody?: string
  bodyClass?: string
}) {
  const heading = title?.trim() ?? ''
  const copy = body?.trim() || fallbackBody?.trim() || ''
  if (!heading && !copy) return null
  return (
    <div className="changes reveal">
      {heading ? <h3>{heading}</h3> : null}
      {copy ? <p className={bodyClass}>{copy}</p> : null}
    </div>
  )
}

function ProblemCards({ items }: { items: string[] }) {
  return (
    <div className="prob-grid">
      {items.map((item, index) => (
        <div key={item} className="prob reveal" data-d={String((index % 3) + 1)}>
          <div className="x">
            <CrossIcon />
          </div>
          <p>{item}</p>
        </div>
      ))}
    </div>
  )
}

function CheckCards({ items, gridClass }: { items: string[]; gridClass: string }) {
  return (
    <div className={gridClass}>
      {items.map((item) => (
        <div key={item} className="able reveal">
          <div className="ck">
            <CheckIcon />
          </div>
          <span>{item}</span>
        </div>
      ))}
    </div>
  )
}

function CovGrid({ items }: { items: string[] }) {
  return (
    <div className="cov-grid reveal" data-d="1">
      {items.map((item) => (
        <div key={item} className="cov">
          <span className="cc">
            <CheckIcon />
          </span>
          <span>{item}</span>
        </div>
      ))}
    </div>
  )
}

export function CourseDetailView({
  course,
  courseId,
  lessons,
  modules,
  courseProgress,
  previewOnly,
  needsAccess,
  onToggleLessonComplete,
  markingLessonId,
}: CourseDetailViewProps) {
  const rootRef = useRef<HTMLDivElement>(null)
  const visual = courseVisualKey(course.title)
  const curriculumNote = visual ? CURRICULUM_NOTES[visual] : undefined
  const page = coursePageFromCourse(course)
  const owned = !previewOnly && !needsAccess
  const price = dollars(priceMinorOf(course))
  const showQuiz = !previewOnly && !needsAccess
  const linkDisabled = previewOnly || needsAccess
  const sections = useMemo(() => groupLessonsByModule(lessons, modules), [lessons, modules])
  const moduleById = useMemo(() => new Map(modules.map((module) => [module.id, module])), [modules])
  const [openIds, setOpenIds] = useState<string[] | null>(null)
  const openSet = new Set(openIds ?? (sections[0] ? [sections[0].id] : []))

  useReveal(rootRef, course.id)

  const subtitle = sectionHasText('subtitle', page)
    ? course.subtitle?.trim()
    : course.description?.trim()
  const checkout = `/checkout?productType=course&courseId=${encodeURIComponent(courseId)}`

  return (
    <div ref={rootRef} className={visual ? `pg-course course-${visual}` : 'pg-course'}>
      <section className="chero" aria-label="Course hero">
        <div className="wrap chero-grid">
          <div>
            <nav className="crumb" aria-label="Breadcrumb">
              <Link to="/">Home</Link>
              <Chevron />
              <Link to="/courses">Courses</Link>
              <Chevron />
              <span style={{ color: 'var(--blue)' }}>{course.title}</span>
            </nav>
            <h1>
              <HeroTitle title={course.title} visual={visual} />
            </h1>
            {subtitle ? <p className="sub">{subtitle}</p> : null}
            <div className="meta-row">
              {price ? (
                <span className="meta-pill price">
                  <DollarIcon /> {price}
                </span>
              ) : null}
              {sectionHasText('estimatedHours', page) && typeof course.estimatedHours === 'number' ? (
                <span className="meta-pill">
                  <ClockIcon /> ~{course.estimatedHours} Hours
                </span>
              ) : null}
              {sectionHasText('level', page) && course.level?.trim() ? (
                <span className="meta-pill">
                  <ChartIcon /> {course.level.trim()}
                </span>
              ) : null}
              <span className="meta-pill">
                <ShieldIcon /> Lifetime Access
              </span>
              <span className="meta-pill">
                <MedalIcon /> Certificate Included
              </span>
            </div>
            <div className="chero-ctas">
              <PrimaryAction
                owned={owned}
                courseId={courseId}
                lessons={lessons}
                modules={modules}
                courseProgress={courseProgress}
              />
              <a href="#curriculum" className="btn btn-ghost">
                View Curriculum
              </a>
            </div>
            {needsAccess ? <p className="sub">{courseDetailNoAccessPrompt}</p> : null}
          </div>
          {visual ? <CourseDetailHeroVisual visual={visual} /> : null}
        </div>
      </section>

      {sectionHasText('problem', page) && page.problem ? (
        <section className="sec problem">
          <div className="wrap">
            <SecHead
              kicker="The Problem"
              title={effectiveSectionHeading(page.problem, DEFAULT_SECTION_HEADINGS.problem)}
              lead={page.problem.lead?.trim()}
              headClass={visual === 'srma' ? 'head-1l' : undefined}
              leadClass={visual === 'srma' ? 'lead-1l' : undefined}
            />
            <ProblemCards items={visibleItems(page.problem.items)} />
            <ProblemCallout
              title={page.problem.calloutTitle}
              body={page.problem.calloutBody}
              fallbackBody={visual ? PROBLEM_CALLOUT_BODY[visual] : undefined}
              bodyClass={visual === 'srma' ? 'balance-2' : undefined}
            />
          </div>
        </section>
      ) : null}

      {sectionHasText('outcomes', page) && page.outcomes ? (
        <section className="sec">
          <div className="wrap">
            <SecHead
              kicker="Outcomes"
              title={effectiveSectionHeading(page.outcomes, DEFAULT_SECTION_HEADINGS.outcomes)}
              lead={page.outcomes.lead?.trim()}
            />
            <CheckCards
              items={visibleItems(page.outcomes.items)}
              gridClass={visual === 'srma' ? 'able-grid able-grid-3x3' : 'able-grid'}
            />
          </div>
        </section>
      ) : null}

      <section className={visual === 'statistics' || visual === 'srma' ? 'sec curriculum-star' : 'sec problem curriculum-star'} id="curriculum">
        <div className="wrap">
          <SecHead kicker="Curriculum" title="Complete Curriculum" lead={page.curriculumLead?.trim()} />
          <div className="cur-meta reveal">
            <div>
              <ModulesIcon /> {countLabel(modules.length, 'Module', 'Modules')}
            </div>
            <div>
              <LessonsIcon /> {countLabel(lessons.length, 'Lesson', 'Lessons')}
            </div>
            {sectionHasText('estimatedHours', page) && typeof course.estimatedHours === 'number' ? (
              <div>
                <ClockIcon /> ~{course.estimatedHours} Hours
              </div>
            ) : null}
          </div>
          <div className="cur-list reveal" data-d="1">
            {sections.map((section, index) => {
              const featured = Boolean(
                (visual && FEATURED_MODULES[visual].has(section.title)) || section.description?.trim(),
              )
              const duration = visual ? MODULE_DURATIONS[visual][section.title] ?? null : null
              return (
                <CurItem
                  key={section.id}
                  index={index}
                  section={section}
                  open={openSet.has(section.id)}
                  onToggle={() => {
                    const current = openIds ?? (sections[0] ? [sections[0].id] : [])
                    setOpenIds(
                      current.includes(section.id)
                        ? current.filter((id) => id !== section.id)
                        : [...current, section.id],
                    )
                  }}
                  courseId={courseId}
                  moduleRow={moduleById.get(section.id)}
                  showQuiz={showQuiz}
                  linkDisabled={linkDisabled}
                  showActions={showQuiz}
                  courseProgress={courseProgress}
                  markingLessonId={markingLessonId}
                  onToggleLessonComplete={onToggleLessonComplete}
                  featured={featured}
                  duration={duration}
                />
              )
            })}
          </div>
          {sections.length === 0 ? <p className="lead">No lessons yet</p> : null}
          {curriculumNote ? (
            <div className="minfo reveal">
              <h3>{curriculumNote.title}</h3>
              <p>{curriculumNote.body}</p>
            </div>
          ) : null}
        </div>
      </section>

      {(sectionHasText('inside', page) && page.inside) || visual === 'srma' ? (
        <section className={visual === 'srma' ? 'sec' : 'sec problem'}>
          <div className="wrap">
            {page.inside && sectionHasText('inside', page) ? (
              <>
                <SecHead
                  kicker="What's Inside"
                  title={effectiveSectionHeading(page.inside, DEFAULT_SECTION_HEADINGS.inside)}
                  lead={page.inside.lead?.trim()}
                  headClass={visual === 'srma' ? 'head-1l' : undefined}
                  leadClass={visual === 'srma' ? 'lead-1l' : undefined}
                />
                <CovGrid items={visibleItems(page.inside.items)} />
              </>
            ) : null}
            {visual === 'srma' ? (
              <>
                <div className="sec-head head-1l" style={{ marginTop: 36 }}>
                  <span className="kicker reveal">Tools You'll Use</span>
                  <p className="lead reveal lead-1l" data-d="1">
                    Hands-on practice with the software and frameworks used in real evidence synthesis projects.
                  </p>
                </div>
                <CovGrid items={[...REVIEW_TOOLS]} />
              </>
            ) : null}
          </div>
        </section>
      ) : null}

      {sectionHasText('handsOn', page) && page.handsOn ? (
        <HandsOn visual={visual} section={page.handsOn} />
      ) : null}

      {visual === 'methodology' ? <StudyDesigns /> : null}
      {visual === 'writing' ? <Rejections /> : null}

      {sectionHasText('highlights', page) && page.highlights ? (
        <Highlights visual={visual} heading={effectiveSectionHeading(page.highlights, DEFAULT_SECTION_HEADINGS.highlights)} lead={page.highlights.lead?.trim()} items={visibleItems(page.highlights.items)} note={page.highlights.closingNote?.trim()} />
      ) : null}

      {sectionHasText('assessment', page) && page.assessment ? (
        <section className={visual === 'writing' || visual === 'srma' ? 'sec problem' : 'sec'}>
          <div className="wrap">
            <SecHead
              kicker="Assessment"
              title={effectiveSectionHeading(page.assessment, DEFAULT_SECTION_HEADINGS.assessment)}
              lead={page.assessment.lead?.trim()}
            />
            <div className="cert-grid">
              <div className="reveal" data-d="1">
                <ol className="cert-steps">
                  {(page.assessment.steps ?? []).map((step, index) =>
                    step.title?.trim() || step.body?.trim() ? (
                      <li key={`${step.title ?? ''}-${index}`}>
                        <span className="cn">{index + 1}</span>
                        <div>
                          {step.title?.trim() ? <h4>{step.title.trim()}</h4> : null}
                          {step.body?.trim() ? (
                            <p>
                              <Emphasized text={step.body.trim()} />
                            </p>
                          ) : null}
                        </div>
                      </li>
                    ) : null,
                  )}
                </ol>
              </div>
              <div className="cert-card reveal" data-d="2">
                <div className="seal">
                  <MedalIcon />
                </div>
                <div className="ct2">Certificate of Completion</div>
                <h3>Research Spectrum</h3>
                <div className="cn2">This is proudly presented to</div>
                <div className="nm">Your Name</div>
                <div className="cs">
                  for completing the <strong>{course.title}</strong> course
                </div>
                <div className="sig">
                  <span>
                    Date Issued<b>Date</b>
                  </span>
                  <span>
                    Research Spectrum<b>Instructor</b>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {sectionHasText('audience', page) && page.audience ? (
        <section className={visual === 'writing' || visual === 'srma' ? 'sec' : 'sec problem'}>
          <div className="wrap">
            <SecHead
              kicker="Who It's For"
              title={effectiveSectionHeading(page.audience, DEFAULT_SECTION_HEADINGS.audience)}
              lead={page.audience.lead?.trim()}
              leadClass={visual === 'statistics' ? 'lead-nowrap' : undefined}
            />
            <CheckCards items={visibleItems(page.audience.items)} gridClass="able-grid" />
          </div>
        </section>
      ) : null}

      {visual ? <Journey visual={visual} /> : null}

        {!owned && sectionHasText('enrollCta', page) && page.enrollCta ? (
        <EnrollBand visual={visual} page={page} price={price} checkout={checkout} />
      ) : null}
    </div>
  )
}

function visibleItems(items: string[] | undefined): string[] {
  return (items ?? []).map((item) => item.trim()).filter(Boolean)
}

function HandsOn({
  visual,
  section,
}: {
  visual: CourseVisualKey | null
  section: NonNullable<CoursePageDocument['handsOn']>
}) {
  const glyphs = visual ? HANDS_ON_GLYPHS[visual] : []
  const cards = (section.cards ?? []).filter((card) => card.title?.trim() || card.body?.trim())
  return (
    <section className={visual === 'writing' || visual === 'srma' ? 'sec problem' : 'sec'}>
      <div className="wrap">
        <SecHead
          kicker="Hands-On Application"
          title={effectiveSectionHeading(section, DEFAULT_SECTION_HEADINGS.handsOn)}
          lead={section.lead?.trim()}
          titleClass={visual === 'writing' ? 'title-1l' : undefined}
          leadClass={visual === 'writing' ? 'lead-3l' : visual === 'srma' ? 'balance-2' : undefined}
          leadStyle={visual === 'statistics' ? { maxWidth: 720 } : undefined}
        />
        <div className="own-grid">
          {cards.map((card, index) => (
            <OwnCard key={`${card.title ?? ''}-${index}`} card={card} glyph={glyphs[index] ?? 'question'} delay={String((index % 4) + 1)} />
          ))}
        </div>
        {section.closingNote?.trim() ? (
          <p className="own-note reveal">
            <Emphasized text={section.closingNote.trim()} />
          </p>
        ) : null}
      </div>
    </section>
  )
}

function OwnCard({ card, glyph, delay }: { card: CoursePageTextCard; glyph: string; delay: string }) {
  return (
    <div className="own reveal" data-d={delay}>
      <div className="oi">
        <OwnGlyph name={glyph} />
      </div>
      {card.title?.trim() ? <h4>{card.title.trim()}</h4> : null}
      {card.body?.trim() ? <p>{card.body.trim()}</p> : null}
    </div>
  )
}

function StudyDesigns() {
  const glyphs = ['table', 'rewind', 'pulse', 'calendar']
  return (
    <section className="sec">
      <div className="wrap">
        <SecHead
          kicker="Quick Reference"
          title="One Concept. Many Study Designs."
          lead="A quick look at the core designs you'll learn to choose between."
          titleStyle={{ whiteSpace: 'nowrap' }}
        />
        <div className="own-grid">
          {STUDY_DESIGNS.map((card, index) => (
            <OwnCard key={card.title} card={card} glyph={glyphs[index] ?? 'question'} delay={String(index + 1)} />
          ))}
        </div>
      </div>
    </section>
  )
}

function Rejections() {
  return (
    <section className="sec">
      <div className="wrap">
        <SecHead
          kicker="Avoidable Pitfalls"
          title="Common Reasons Manuscripts Get Rejected"
          lead="Many submissions are rejected for preventable reasons. Learn how to avoid the most common mistakes before your manuscript reaches a reviewer."
        />
        <ProblemCards items={[...REJECTION_ITEMS]} />
        <div className="changes reveal">
          <h3>Avoid The Mistakes That Delay Publication</h3>
          <p>
            Learn the standards, structure, and writing techniques expected by journals and reviewers — every one of these problems is solvable with the right framework.
          </p>
        </div>
      </div>
    </section>
  )
}

function Highlights({
  visual,
  heading,
  lead,
  items,
  note,
}: {
  visual: CourseVisualKey | null
  heading: string
  lead?: string
  items: string[]
  note?: string
}) {
  const jpath = visual === 'writing' || visual === 'srma'
  const glyphs = visual ? HIGHLIGHT_GLYPHS[visual] ?? [] : []
  return (
    <section className={jpath || visual === null ? 'sec' : 'sec problem'}>
      <div className="wrap">
        <SecHead
          kicker={visual === 'writing' ? 'The Transformation' : 'The Workflow'}
          title={heading}
          lead={lead}
          titleStyle={visual === 'methodology' ? { whiteSpace: 'nowrap' } : undefined}
          leadClass={visual === 'writing' ? 'lead-1l' : undefined}
        />
        {jpath ? (
          <div className="jpath reveal" data-d="1">
            {items.map((item, index) => (
              <span key={item} style={{ display: 'contents' }}>
                {index > 0 ? (
                  <span className="jarrow">
                    <Arrow />
                  </span>
                ) : null}
                <span className={index === items.length - 1 ? 'jstep final' : 'jstep'}>
                  <span className="jn">{index + 1}</span> {item}
                </span>
              </span>
            ))}
          </div>
        ) : (
          <div className="pub-grid">
            {items.map((item, index) => (
              <div key={item} className="pub reveal" data-d={String((index % 3) + 1)}>
                <div className="pi">
                  <OwnGlyph name={glyphs[index] ?? 'file'} />
                </div>
                <h4>{item}</h4>
              </div>
            ))}
          </div>
        )}
        {note ? (
          <p className="pub-note reveal">
            <Emphasized text={note} />
          </p>
        ) : null}
      </div>
    </section>
  )
}

function Journey({ visual }: { visual: CourseVisualKey }) {
  const copy = JOURNEY[visual]
  return (
    <section className={copy.sectionClass}>
      <div className="wrap">
        <SecHead kicker="The Bigger Picture" title="Part of a Bigger Research Journey" lead={copy.lead} />
        <div className="road reveal" data-d="1">
          {JOURNEY_STEPS.map((title, index) => {
            const current = index === copy.current
            const final = index === JOURNEY_STEPS.length - 1
            const num = current ? 'YOU ARE HERE' : final ? 'GOAL' : `STEP 0${index + 1}`
            const className = final ? 'step final' : current ? 'step cur' : 'step'
            return (
              <div key={title} className={className}>
                <div className="node">
                  <OwnGlyph name={JOURNEY_GLYPHS[index] ?? 'file'} />
                </div>
                <span className="num">{num}</span>
                <h4>{title}</h4>
              </div>
            )
          })}
        </div>
        <p className="path-note reveal" data-d="2">
          {copy.note}
        </p>
      </div>
    </section>
  )
}

function EnrollBand({
  visual,
  page,
  price,
  checkout,
}: {
  visual: CourseVisualKey | null
  page: CoursePageDocument
  price: string | null
  checkout: string
}) {
  const section = page.enrollCta
  if (!section) return null
  const heading = effectiveSectionHeading(section, DEFAULT_SECTION_HEADINGS.enrollCta)
  const body = section.body?.trim()
  return (
    <section className="cta-band" id="enroll">
      <div className="wrap">
        <div className="cta-inner reveal">
          <h2>{heading}</h2>
          {body ? <CtaBody text={body} visual={visual} /> : null}
          {section.extraLine?.trim() ? <p className="cta-extra">{section.extraLine.trim()}</p> : null}
          <div className="cta-meta">
            {price ? (
              <span>
                <DollarIcon sw="2.2" /> {price}
              </span>
            ) : null}
            <span>
              <ShieldIcon sw="2.2" /> Lifetime Access
            </span>
            <span>
              <MedalIcon sw="2.2" /> Certificate Included
            </span>
          </div>
          <div className="btn-w">
            <Link to={checkout} className="btn btn-white">
              Enroll Now <Arrow />
            </Link>
            <a href="#curriculum" className="btn" style={{ background: 'transparent', color: '#fff', border: '1.5px solid rgba(255,255,255,.5)' }}>
              View Curriculum
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}

function CtaBody({ text, visual }: { text: string; visual: CourseVisualKey | null }) {
  if (visual === 'statistics') {
    const marker = 'analyze data in SPSS,'
    const at = text.indexOf(marker)
    if (at !== -1) {
      const cut = at + marker.length
      return (
        <p>
          {text.slice(0, cut)}
          <br className="desktop-br" />
          {text.slice(cut)}
        </p>
      )
    }
  }
  return <p>{text}</p>
}
