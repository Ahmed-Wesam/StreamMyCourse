import type {
  CoursePageDocument,
  CoursePageHandsOnSection,
  CoursePageListSection,
  CoursePageProblemSection,
  CoursePageTextCard,
} from '../../lib/course-page'
import { DEFAULT_SECTION_HEADINGS } from '../../lib/course-page'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Field } from '../ui/Field'

type CoursePageContentEditorProps = {
  page: CoursePageDocument
  onPageChange: (page: CoursePageDocument) => void
  onSave: () => void
  saving?: boolean
}

function updateProblem(
  page: CoursePageDocument,
  patch: Partial<CoursePageProblemSection>,
): CoursePageDocument {
  return { ...page, problem: { ...page.problem, ...patch } }
}

function updateHandsOn(
  page: CoursePageDocument,
  patch: Partial<CoursePageHandsOnSection>,
): CoursePageDocument {
  return { ...page, handsOn: { ...page.handsOn, ...patch } }
}

function StringListField({
  label,
  items,
  addLabel,
  removeLabel,
  itemLabel,
  onChange,
}: {
  label: string
  items: string[]
  addLabel: string
  removeLabel: string
  itemLabel: string
  onChange: (items: string[]) => void
}) {
  const rows = items.length > 0 ? items : ['']

  return (
    <div className="mb-4">
      <p className="mb-2 text-sm font-semibold text-rs-navy">{label}</p>
      <ul className="space-y-2">
        {rows.map((item, index) => (
          <li key={index} className="flex gap-2">
            <Field
              label={itemLabel}
              className="mb-0 flex-1"
              value={item}
              onChange={(e) => {
                const next = [...rows]
                next[index] = e.target.value
                onChange(next)
              }}
            />
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="mt-7 shrink-0"
              aria-label={removeLabel}
              onClick={() => {
                const next = rows.filter((_, i) => i !== index)
                onChange(next.length > 0 ? next : [''])
              }}
            >
              Remove
            </Button>
          </li>
        ))}
      </ul>
      <Button
        type="button"
        size="sm"
        variant="ghost"
        className="mt-2"
        onClick={() => onChange([...rows, ''])}
      >
        {addLabel}
      </Button>
    </div>
  )
}

function ListSectionFields({
  headingDefault,
  section,
  onChange,
}: {
  headingDefault: string
  section: CoursePageListSection | undefined
  onChange: (section: CoursePageListSection) => void
}) {
  const value = section ?? {}
  return (
    <>
      <Field
        label="Section heading"
        hint={`Default: ${headingDefault}`}
        className="mb-4"
        value={value.heading ?? ''}
        onChange={(e) => onChange({ ...value, heading: e.target.value })}
      />
      <Field label="Lead" className="mb-4">
        <textarea
          value={value.lead ?? ''}
          onChange={(e) => onChange({ ...value, lead: e.target.value })}
          rows={2}
          className="w-full rounded-xl border-[1.5px] border-solid border-rs-line px-[14px] py-[11px] text-[15px] text-rs-ink"
        />
      </Field>
      <StringListField
        label="List items"
        items={value.items ?? []}
        addLabel="Add list item"
        removeLabel="Remove list item"
        itemLabel="List item"
        onChange={(items) => onChange({ ...value, items })}
      />
    </>
  )
}

function TextCardListField({
  label,
  cards,
  addLabel,
  removeLabel,
  onChange,
}: {
  label: string
  cards: CoursePageTextCard[] | undefined
  addLabel: string
  removeLabel: string
  onChange: (cards: CoursePageTextCard[]) => void
}) {
  const rows = cards && cards.length > 0 ? cards : [{ title: '', body: '' }]

  return (
    <div className="mb-4">
      <p className="mb-2 text-sm font-semibold text-rs-navy">{label}</p>
      <ul className="space-y-4">
        {rows.map((card, index) => (
          <li key={index} className="rounded-lg border border-rs-line p-4">
            <Field
              label="Title"
              className="mb-3"
              value={card.title ?? ''}
              onChange={(e) => {
                const next = [...rows]
                next[index] = { ...next[index], title: e.target.value }
                onChange(next)
              }}
            />
            <Field label="Body" className="mb-3">
              <textarea
                value={card.body ?? ''}
                onChange={(e) => {
                  const next = [...rows]
                  next[index] = { ...next[index], body: e.target.value }
                  onChange(next)
                }}
                rows={2}
                className="w-full rounded-xl border-[1.5px] border-solid border-rs-line px-[14px] py-[11px] text-[15px] text-rs-ink"
              />
            </Field>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              aria-label={removeLabel}
              onClick={() => {
                const next = rows.filter((_, i) => i !== index)
                onChange(next.length > 0 ? next : [{ title: '', body: '' }])
              }}
            >
              Remove card
            </Button>
          </li>
        ))}
      </ul>
      <Button type="button" size="sm" variant="ghost" className="mt-2" onClick={() => onChange([...rows, {}])}>
        {addLabel}
      </Button>
    </div>
  )
}

const textareaClass =
  'w-full rounded-xl border-[1.5px] border-solid border-rs-line px-[14px] py-[11px] text-[15px] text-rs-ink'

function PageMetaFields({
  page,
  onPageChange,
}: {
  page: CoursePageDocument
  onPageChange: (page: CoursePageDocument) => void
}) {
  return (
    <>
      <Field
        label="Subtitle"
        className="mb-4"
        value={page.subtitle ?? ''}
        onChange={(e) => onPageChange({ ...page, subtitle: e.target.value })}
      />
      <Field
        label="Level"
        className="mb-4"
        value={page.level ?? ''}
        onChange={(e) => onPageChange({ ...page, level: e.target.value })}
      />
      <Field
        label="Estimated hours"
        type="number"
        min={0}
        step={0.5}
        className="mb-4"
        value={page.estimatedHours ?? ''}
        onChange={(e) => {
          const raw = e.target.value
          onPageChange({
            ...page,
            estimatedHours: raw === '' ? undefined : Number(raw),
          })
        }}
      />
      <StringListField
        label="Catalog skills"
        items={page.catalogSkills ?? []}
        addLabel="Add catalog skill"
        removeLabel="Remove catalog skill"
        itemLabel="Catalog skill"
        onChange={(catalogSkills) => onPageChange({ ...page, catalogSkills })}
      />
      <Field label="Curriculum lead" className="mb-4">
        <textarea
          value={page.curriculumLead ?? ''}
          onChange={(e) => onPageChange({ ...page, curriculumLead: e.target.value })}
          rows={2}
          className={textareaClass}
        />
      </Field>
    </>
  )
}

function ProblemSection({
  page,
  onPageChange,
}: {
  page: CoursePageDocument
  onPageChange: (page: CoursePageDocument) => void
}) {
  return (
    <>
      <h3 className="mb-3 text-lg font-bold text-rs-navy">Problem</h3>
      <ListSectionFields
        headingDefault={DEFAULT_SECTION_HEADINGS.problem}
        section={page.problem}
        onChange={(problem) => onPageChange({ ...page, problem })}
      />
      <Field
        label="Callout title"
        className="mb-4"
        value={page.problem?.calloutTitle ?? ''}
        onChange={(e) => onPageChange(updateProblem(page, { calloutTitle: e.target.value }))}
      />
      <Field label="Callout body" className="mb-6">
        <textarea
          value={page.problem?.calloutBody ?? ''}
          onChange={(e) => onPageChange(updateProblem(page, { calloutBody: e.target.value }))}
          rows={2}
          className={textareaClass}
        />
      </Field>
    </>
  )
}

function HandsOnSection({
  page,
  onPageChange,
}: {
  page: CoursePageDocument
  onPageChange: (page: CoursePageDocument) => void
}) {
  return (
    <>
      <h3 className="mb-3 text-lg font-bold text-rs-navy">Hands-on</h3>
      <Field
        label="Section heading"
        hint={`Default: ${DEFAULT_SECTION_HEADINGS.handsOn}`}
        className="mb-4"
        value={page.handsOn?.heading ?? ''}
        onChange={(e) => onPageChange(updateHandsOn(page, { heading: e.target.value }))}
      />
      <Field label="Lead" className="mb-4">
        <textarea
          value={page.handsOn?.lead ?? ''}
          onChange={(e) => onPageChange(updateHandsOn(page, { lead: e.target.value }))}
          rows={2}
          className={textareaClass}
        />
      </Field>
      <TextCardListField
        label="Cards"
        cards={page.handsOn?.cards}
        addLabel="Add card"
        removeLabel="Remove card"
        onChange={(cards) => onPageChange(updateHandsOn(page, { cards }))}
      />
      <Field label="Closing note" className="mb-6">
        <textarea
          value={page.handsOn?.closingNote ?? ''}
          onChange={(e) => onPageChange(updateHandsOn(page, { closingNote: e.target.value }))}
          rows={2}
          className={textareaClass}
        />
      </Field>
    </>
  )
}

function HighlightsSection({
  page,
  onPageChange,
}: {
  page: CoursePageDocument
  onPageChange: (page: CoursePageDocument) => void
}) {
  return (
    <>
      <h3 className="mb-3 text-lg font-bold text-rs-navy">Highlights</h3>
      <Field
        label="Section heading"
        hint={`Default: ${DEFAULT_SECTION_HEADINGS.highlights}`}
        className="mb-4"
        value={page.highlights?.heading ?? ''}
        onChange={(e) =>
          onPageChange({ ...page, highlights: { ...page.highlights, heading: e.target.value } })
        }
      />
      <Field label="Lead" className="mb-4">
        <textarea
          value={page.highlights?.lead ?? ''}
          onChange={(e) =>
            onPageChange({ ...page, highlights: { ...page.highlights, lead: e.target.value } })
          }
          rows={2}
          className={textareaClass}
        />
      </Field>
      <StringListField
        label="Highlight items"
        items={page.highlights?.items ?? []}
        addLabel="Add highlight"
        removeLabel="Remove highlight"
        itemLabel="Highlight"
        onChange={(items) =>
          onPageChange({ ...page, highlights: { ...page.highlights, items } })
        }
      />
      <Field label="Closing note" className="mb-6">
        <textarea
          value={page.highlights?.closingNote ?? ''}
          onChange={(e) =>
            onPageChange({ ...page, highlights: { ...page.highlights, closingNote: e.target.value } })
          }
          rows={2}
          className={textareaClass}
        />
      </Field>
    </>
  )
}

function AssessmentSection({
  page,
  onPageChange,
}: {
  page: CoursePageDocument
  onPageChange: (page: CoursePageDocument) => void
}) {
  return (
    <>
      <h3 className="mb-3 text-lg font-bold text-rs-navy">Assessment</h3>
      <Field
        label="Section heading"
        hint={`Default: ${DEFAULT_SECTION_HEADINGS.assessment}`}
        className="mb-4"
        value={page.assessment?.heading ?? ''}
        onChange={(e) =>
          onPageChange({ ...page, assessment: { ...page.assessment, heading: e.target.value } })
        }
      />
      <Field label="Lead" className="mb-4">
        <textarea
          value={page.assessment?.lead ?? ''}
          onChange={(e) =>
            onPageChange({ ...page, assessment: { ...page.assessment, lead: e.target.value } })
          }
          rows={2}
          className={textareaClass}
        />
      </Field>
      <TextCardListField
        label="Steps"
        cards={page.assessment?.steps}
        addLabel="Add step"
        removeLabel="Remove step"
        onChange={(steps) => onPageChange({ ...page, assessment: { ...page.assessment, steps } })}
      />
    </>
  )
}

function EnrollCtaSection({
  page,
  onPageChange,
}: {
  page: CoursePageDocument
  onPageChange: (page: CoursePageDocument) => void
}) {
  return (
    <>
      <h3 className="mb-3 text-lg font-bold text-rs-navy">Enroll CTA</h3>
      <Field
        label="Heading"
        hint={`Default: ${DEFAULT_SECTION_HEADINGS.enrollCta}`}
        className="mb-4"
        value={page.enrollCta?.heading ?? ''}
        onChange={(e) =>
          onPageChange({ ...page, enrollCta: { ...page.enrollCta, heading: e.target.value } })
        }
      />
      <Field label="Body" className="mb-4">
        <textarea
          value={page.enrollCta?.body ?? ''}
          onChange={(e) =>
            onPageChange({ ...page, enrollCta: { ...page.enrollCta, body: e.target.value } })
          }
          rows={2}
          className={textareaClass}
        />
      </Field>
      <Field
        label="Extra line"
        className="mb-6"
        value={page.enrollCta?.extraLine ?? ''}
        onChange={(e) =>
          onPageChange({ ...page, enrollCta: { ...page.enrollCta, extraLine: e.target.value } })
        }
      />
    </>
  )
}

export function CoursePageContentEditor({
  page,
  onPageChange,
  onSave,
  saving = false,
}: CoursePageContentEditorProps) {
  return (
    <Card className="mb-6 p-6" data-testid="course-page-content-editor">
      <h2 className="mb-2 text-xl font-extrabold text-rs-navy">Course page content</h2>
      <p className="mb-6 text-sm text-rs-body">
        Marketing sections shown on the public course detail page. Saved together with the current title and
        description; price is saved separately.
      </p>

      <PageMetaFields page={page} onPageChange={onPageChange} />
      <ProblemSection page={page} onPageChange={onPageChange} />

      <h3 className="mb-3 text-lg font-bold text-rs-navy">Outcomes</h3>
      <ListSectionFields
        headingDefault={DEFAULT_SECTION_HEADINGS.outcomes}
        section={page.outcomes}
        onChange={(outcomes) => onPageChange({ ...page, outcomes })}
      />

      <h3 className="mb-3 text-lg font-bold text-rs-navy">Inside the course</h3>
      <ListSectionFields
        headingDefault={DEFAULT_SECTION_HEADINGS.inside}
        section={page.inside}
        onChange={(inside) => onPageChange({ ...page, inside })}
      />

      <HandsOnSection page={page} onPageChange={onPageChange} />
      <HighlightsSection page={page} onPageChange={onPageChange} />

      <h3 className="mb-3 text-lg font-bold text-rs-navy">Audience</h3>
      <ListSectionFields
        headingDefault={DEFAULT_SECTION_HEADINGS.audience}
        section={page.audience}
        onChange={(audience) => onPageChange({ ...page, audience })}
      />

      <AssessmentSection page={page} onPageChange={onPageChange} />
      <EnrollCtaSection page={page} onPageChange={onPageChange} />

      <Button type="button" onClick={onSave} disabled={saving}>
        {saving ? 'Saving page content…' : 'Save page content'}
      </Button>
    </Card>
  )
}
