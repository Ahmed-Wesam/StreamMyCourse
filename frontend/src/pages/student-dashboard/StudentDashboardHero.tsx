type StudentDashboardHeroProps = {
  givenName: string | null
}

export function StudentDashboardHero({ givenName }: StudentDashboardHeroProps) {
  const headline = givenName?.trim() ? `Welcome back, ${givenName.trim()}` : 'Welcome back'

  return (
    <section className="border-b border-rs-line bg-rs-grad-soft px-5 py-12 sm:px-7 sm:py-16">
      <div className="mx-auto max-w-wrap">
        <h1 className="text-3xl font-extrabold tracking-tight text-rs-ink sm:text-4xl">{headline}</h1>
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-rs-body">
          Pick up where you left off across your courses.
        </p>
      </div>
    </section>
  )
}
