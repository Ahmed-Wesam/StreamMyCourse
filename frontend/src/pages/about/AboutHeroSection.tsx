import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Eyebrow } from '../../components/ui/Eyebrow'
import { Reveal } from '../../components/ui/Reveal'
import { Badge } from '../../components/ui/Badge'
import instructorPhoto from '../../assets/instructors/dr-bahaa-aburayya.webp'
import { aboutHero } from '../../lib/marketing/aboutCopy'

export function AboutHeroSection() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-rs-sky-2 to-white px-5 py-16 sm:px-7 sm:py-[68px]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(720px_480px_at_85%_10%,rgba(58,134,255,.11),transparent_62%),radial-gradient(500px_360px_at_0%_50%,rgba(30,94,255,.06),transparent_60%)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-40 [background-image:radial-gradient(rgba(30,94,255,.10)_1px,transparent_1px)] [background-size:30px_30px] [mask-image:radial-gradient(680px_480px_at_25%_35%,#000,transparent_72%)]"
      />

      <div className="relative mx-auto grid max-w-wrap items-center gap-12 nav:grid-cols-[1.1fr_0.9fr] nav:gap-[60px]">
        <div>
          <Reveal>
            <Eyebrow>{aboutHero.eyebrow}</Eyebrow>
          </Reveal>
          <Reveal>
            <h1 className="mt-4 text-[clamp(36px,4.8vw,56px)] font-extrabold leading-[1.06] tracking-tight text-rs-ink">
              {aboutHero.nameLine1}
              <br />
              <span className="bg-rs-grad-cta bg-clip-text text-transparent">
                {aboutHero.nameHighlight}
              </span>
            </h1>
          </Reveal>
          <Reveal>
            <p className="mt-5 max-w-[520px] text-[17.5px] leading-relaxed text-rs-body">
              {aboutHero.sub}
            </p>
          </Reveal>
          <Reveal>
            <div className="mt-[30px] flex flex-wrap gap-3.5">
              <Button to="/courses" arrow>
                {aboutHero.primaryCta}
              </Button>
              <Button href="#story" variant="ghost">
                {aboutHero.secondaryCta}
              </Button>
            </div>
          </Reveal>
        </div>

        <Reveal>
          <Card className="relative overflow-hidden rounded-rs-lg px-7 py-8 text-center shadow-rs-lg">
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 bg-[radial-gradient(420px_200px_at_50%_0%,rgba(30,94,255,.04),transparent)]"
            />
            <div className="relative">
              <div className="mx-auto mb-4 size-[88px] overflow-hidden rounded-full border-4 border-white outline outline-[3px] outline-[rgba(30,94,255,.18)] shadow-[0_14px_28px_-8px_rgba(30,94,255,.45)]">
                <img
                  src={instructorPhoto}
                  alt="Dr. Bahaa Aburayya"
                  className="size-full object-cover"
                  width={88}
                  height={88}
                />
              </div>
              <p className="text-xl font-extrabold tracking-tight text-rs-ink">{aboutHero.fullName}</p>
              <p className="mt-1.5 text-[13.5px] font-semibold text-rs-muted">{aboutHero.titleLine}</p>
              <div className="mt-4 flex flex-wrap justify-center gap-1.5">
                {aboutHero.roles.map((role) => (
                  <Badge key={role} tone="blue">
                    {role}
                  </Badge>
                ))}
              </div>
              <div className="mt-5 grid grid-cols-2 gap-2.5">
                {aboutHero.stats.map((stat) => (
                  <div
                    key={stat.label}
                    className="rounded-[14px] border border-rs-line-2 bg-rs-sky-2 px-3 py-3.5 text-center"
                  >
                    <div
                      className={[
                        'font-extrabold tracking-tight text-rs-ink',
                        stat.value.length <= 2
                          ? 'text-xl leading-none'
                          : 'text-xs leading-tight whitespace-nowrap overflow-hidden',
                      ].join(' ')}
                    >
                      {stat.value}
                    </div>
                    <div className="mt-1 text-[10.5px] font-bold uppercase tracking-wider text-rs-muted">
                      {stat.label}
                    </div>
                  </div>
                ))}
              </div>
              <Button to="/courses" size="sm" arrow className="mt-[22px] w-full justify-center">
                {aboutHero.primaryCta}
              </Button>
            </div>
          </Card>
        </Reveal>
      </div>
    </section>
  )
}
