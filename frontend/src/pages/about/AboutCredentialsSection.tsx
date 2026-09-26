import {
  BookOpen,
  Building2,
  GraduationCap,
  LineChart,
  Shield,
} from 'lucide-react'
import type { ReactNode } from 'react'

import instructorPhoto from '../../assets/instructors/dr-bahaa-aburayya.webp'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { aboutCredentials } from '../../lib/marketing/aboutCopy'

const iconMap: Record<(typeof aboutCredentials.items)[number]['icon'], ReactNode> = {
  graduation: <GraduationCap aria-hidden className="size-[19px]" strokeWidth={2} />,
  shield: <Shield aria-hidden className="size-[19px]" strokeWidth={2} />,
  building: <Building2 aria-hidden className="size-[19px]" strokeWidth={2} />,
  book: <BookOpen aria-hidden className="size-[19px]" strokeWidth={2} />,
  chart: <LineChart aria-hidden className="size-[19px]" strokeWidth={2} />,
}

export function AboutCredentialsSection() {
  return (
    <section id="profile" className="scroll-mt-24 border-y border-rs-line-2 bg-rs-sky-2 px-5 py-20 sm:px-7">
      <div className="mx-auto max-w-wrap">
        <Reveal>
          <div className="mb-10">
            <SectionHeader
              kicker={aboutCredentials.kicker}
              title={aboutCredentials.title}
              lead={aboutCredentials.lead}
            />
          </div>
        </Reveal>

        <div className="grid items-start gap-8 nav:grid-cols-[260px_1fr] nav:gap-[52px]">
          <Reveal>
            <div className="mx-auto w-full max-w-[240px] nav:mx-0 nav:max-w-none">
              <div className="relative aspect-[3/4] overflow-hidden rounded-rs-lg border border-rs-line shadow-rs">
                <img
                  src={instructorPhoto}
                  alt="Dr. Bahaa Aburayya"
                  className="absolute inset-0 size-full object-cover"
                />
                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-[rgba(8,18,41,.82)] via-[rgba(8,18,41,.32)] to-transparent px-3 pb-3.5 pt-[30px] text-center text-[11px] font-extrabold uppercase tracking-widest text-white">
                  {aboutCredentials.name}
                </div>
              </div>
            </div>
          </Reveal>

          <Reveal>
            <div>
              <p className="text-[22px] font-extrabold tracking-tight text-rs-ink">
                {aboutCredentials.name}
              </p>
              <p className="mt-1.5 text-[15px] font-semibold text-rs-muted">
                {aboutCredentials.subtitle}
              </p>
              <p className="mt-[22px] text-[15.5px] leading-relaxed text-rs-body">
                {aboutCredentials.bio}
              </p>
              <div className="mt-[22px] mb-[30px] flex flex-wrap gap-2.5">
                {aboutCredentials.profileLinks.map((link) => (
                  <Button
                    key={link.href}
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    variant={link.variant}
                    size="sm"
                    arrow
                  >
                    {link.label}
                  </Button>
                ))}
              </div>
              <div className="flex flex-col gap-[18px]">
                {aboutCredentials.items.map((item) => (
                  <Card
                    key={item.role}
                    className="flex gap-4 rounded-2xl p-[18px] shadow-rs-sm"
                  >
                    <div
                      className={[
                        'flex size-[42px] shrink-0 items-center justify-center rounded-xl border',
                        item.icon === 'chart'
                          ? 'border-[#bce7c8] bg-[#dcf5e3] text-[#0d6f3e]'
                          : 'border-[#e2ebff] bg-rs-grad-soft text-rs-blue',
                      ].join(' ')}
                    >
                      {iconMap[item.icon]}
                    </div>
                    <div className="min-w-0">
                      <p className="text-[15.5px] font-extrabold tracking-tight text-rs-ink">
                        {item.role}
                      </p>
                      <p className="mt-0.5 text-sm font-bold text-rs-blue">{item.org}</p>
                      <p className="mt-0.5 text-[13px] font-semibold leading-snug text-rs-muted">
                        {item.detail}
                      </p>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
