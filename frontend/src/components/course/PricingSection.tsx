import { useMemo, useState } from 'react'
import { FIGMA_MOCK_COURSE_PRICING_PLANS } from '../../lib/figma-mocks'

type PricingPlan = (typeof FIGMA_MOCK_COURSE_PRICING_PLANS)[number]

function PlanCard({
  plan,
  selected,
  onSelect,
}: {
  plan: PricingPlan
  selected: boolean
  onSelect: () => void
}) {
  const border = selected
    ? 'border-blue-600 shadow-lg shadow-blue-600/10'
    : 'border-slate-200 hover:border-slate-300'

  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onSelect}
      className={`relative flex w-full cursor-pointer flex-col rounded-2xl border-2 bg-white p-8 text-left transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500 ${border}`}
      data-testid={`pricing-plan-${plan.id}`}
    >
      {plan.badge && (
        <div
          className={`absolute -top-3.5 left-1/2 -translate-x-1/2 rounded-full px-4 py-1 text-xs font-semibold whitespace-nowrap ${
            plan.highlight ? 'bg-blue-600 text-white' : 'bg-slate-900 text-white'
          }`}
        >
          {plan.badge}
        </div>
      )}

      <div className="mb-6">
        <h3 className="mb-1 text-lg font-semibold text-slate-900">{plan.duration}</h3>
        <div className="mt-3 flex items-end gap-1">
          <span className="text-[2.5rem] font-bold leading-none text-blue-600">${plan.price}</span>
          <span className="mb-1 text-slate-500">total</span>
        </div>
        <p className="mt-1 text-sm text-slate-500">
          ~${plan.perMonth}/month · {plan.billing}
        </p>
        {plan.savings && (
          <div className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs text-emerald-700">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" aria-hidden="true" />
            Save ${plan.savings} ({plan.savingsPct} off)
          </div>
        )}
      </div>

      <ul className="mb-8 flex-1 space-y-2.5 text-sm text-slate-600">
        {plan.perks.map((perk) => (
          <li key={perk} className="flex items-start gap-2.5">
            <span className="mt-1 inline-block h-4 w-4 shrink-0 rounded-full bg-blue-600/10" aria-hidden="true" />
            <span>{perk}</span>
          </li>
        ))}
      </ul>

      <div
        className={`w-full rounded-lg py-3.5 text-center font-semibold transition-colors ${
          selected ? 'bg-blue-600 text-white' : 'border border-slate-200 bg-slate-50 text-slate-900'
        }`}
        aria-hidden="true"
      >
        {selected ? 'Enroll Now' : 'Select Plan'}
      </div>
    </button>
  )
}

export function PricingSection({ id }: { id?: string }) {
  const [selectedPlanId, setSelectedPlanId] = useState<string>(FIGMA_MOCK_COURSE_PRICING_PLANS[1]?.id ?? 'default')

  const selectedPlan = useMemo(
    () => FIGMA_MOCK_COURSE_PRICING_PLANS.find((p) => p.id === selectedPlanId),
    [selectedPlanId],
  )

  return (
    <section
      id={id}
      aria-label="Pricing"
      data-testid="course-pricing"
      className="rounded-2xl bg-slate-50/80 py-14 ring-1 ring-slate-200 sm:py-16"
    >
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <h2 className="text-center text-2xl font-bold text-slate-900 sm:text-3xl">Choose Your Plan</h2>
        <p className="mx-auto mt-3 max-w-2xl text-center text-slate-600">
          Flexible access options — pick the duration that fits your learning pace.
        </p>

        <div
          role="radiogroup"
          aria-label="Course plan options"
          className="mt-10 grid gap-6 md:grid-cols-3 md:items-stretch"
        >
          {FIGMA_MOCK_COURSE_PRICING_PLANS.map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              selected={plan.id === selectedPlanId}
              onSelect={() => setSelectedPlanId(plan.id)}
            />
          ))}
        </div>

        <div className="mx-auto mt-10 flex max-w-3xl flex-col items-center justify-center gap-3 text-center text-sm text-slate-600 sm:flex-row sm:text-left">
          <span className="inline-block h-9 w-9 shrink-0 rounded-full bg-blue-600/10" aria-hidden="true" />
          <span>
            All plans include a <strong className="text-slate-900">7-day money-back guarantee</strong>. If you're not
            satisfied, we'll refund you in full — no questions asked.
          </span>
        </div>

        {selectedPlan && (
          <p className="sr-only" aria-live="polite">
            Selected plan: {selectedPlan.duration}
          </p>
        )}
      </div>
    </section>
  )
}

