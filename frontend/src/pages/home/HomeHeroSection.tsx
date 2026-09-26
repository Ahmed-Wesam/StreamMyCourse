import { BarChart2, Check, Medal } from 'lucide-react'
import type { ReactNode } from 'react'

import { Button } from '../../components/ui/Button'
import { Eyebrow } from '../../components/ui/Eyebrow'
import { homeHero } from '../../lib/marketing/homeCopy'

export function HomeHeroSection() {
  return (
    <section className="relative overflow-hidden px-5 py-16 sm:px-7 sm:py-[88px]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-20 bg-[radial-gradient(620px_480px_at_88%_6%,rgba(58,134,255,.14),transparent_60%),radial-gradient(540px_420px_at_6%_30%,rgba(30,94,255,.08),transparent_60%)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 opacity-50 [background-image:radial-gradient(rgba(30,94,255,.10)_1px,transparent_1px)] [background-size:30px_30px] [mask-image:radial-gradient(700px_540px_at_50%_18%,#000,transparent_72%)]"
      />

      <div className="mx-auto grid max-w-wrap items-center gap-12 nav:grid-cols-[1.05fr_1fr] nav:gap-12">
        <div>
          <Eyebrow>{homeHero.eyebrow}</Eyebrow>
          <h1 className="mt-[22px] text-[clamp(36px,5.2vw,58px)] font-extrabold leading-[1.05] tracking-tight text-rs-ink">
            {homeHero.headlineBefore}
            <span className="bg-rs-grad-cta bg-clip-text text-transparent">
              {homeHero.headlineHighlight}
            </span>
          </h1>
          <p className="mt-5 max-w-[520px] text-[18.5px] leading-relaxed text-rs-body">
            {homeHero.sub}
          </p>
          <div className="mt-8 flex flex-wrap gap-3.5">
            <Button to="/courses" arrow>
              {homeHero.primaryCta}
            </Button>
            <Button href="#courses" variant="ghost">
              {homeHero.secondaryCta}
            </Button>
          </div>
          <div className="mt-[26px] inline-flex items-center gap-2.5 rounded-full border border-rs-line bg-white px-4 py-2.5 text-[14.5px] font-semibold text-rs-navy shadow-rs-sm">
            <Check aria-hidden className="size-[18px] shrink-0 text-rs-blue" strokeWidth={2.2} />
            {homeHero.authNote}
          </div>
        </div>

        <div className="relative mx-auto h-[340px] w-full max-w-[480px] sm:h-[420px] nav:h-[480px]">
          <LaptopGraphic />
          <div className="absolute bottom-[30px] right-0 z-[3] w-[150px] -rotate-1 sm:w-[220px] nav:w-[300px]">
            {homeHero.bookLabels.map((label, index) => (
              <div
                key={label}
                className={[
                  'relative mt-[-7px] flex h-[42px] items-center justify-center rounded-lg px-4 text-[12px] font-extrabold tracking-wide text-white shadow-[0_12px_28px_-10px_rgba(12,30,80,.55)] sm:h-[54px] sm:text-[15.5px]',
                  index === 0 && 'ml-0 w-[92%] bg-gradient-to-r from-rs-navy-800 to-[#1b3c8f]',
                  index === 1 && 'ml-1 w-[92%] bg-gradient-to-r from-[#16399c] to-[#2256d6] sm:ml-2',
                  index === 2 && 'ml-2 w-[92%] bg-gradient-to-r from-rs-blue to-rs-blue-500 sm:ml-4',
                  index === 3 &&
                    'ml-3 w-[92%] bg-gradient-to-r from-rs-blue-500 to-[#5aa0ff] sm:ml-6',
                ]
                  .filter(Boolean)
                  .join(' ')}
              >
                <span
                  aria-hidden
                  className="absolute left-2.5 top-1/2 h-[55%] w-1 -translate-y-1/2 rounded-sm bg-white/50"
                />
                {label}
              </div>
            ))}
          </div>

          <FloatCard
            className="left-[18px] top-2 rs-hero-float"
            icon={<BarChart2 aria-hidden className="size-5" strokeWidth={2.2} />}
            iconClass="bg-rs-grad-cta"
            label={homeHero.floatCards[0].label}
            value={homeHero.floatCards[0].value}
          />
          <FloatCard
            className="-left-2 bottom-[54px] rs-hero-float rs-hero-float-d1 sm:-left-3.5"
            icon={<Check aria-hidden className="size-5" strokeWidth={2.2} />}
            iconClass="bg-gradient-to-br from-[#16a34a] to-[#22c55e]"
            label={homeHero.floatCards[1].label}
            value={homeHero.floatCards[1].value}
          />
          <FloatCard
            className="right-0 top-[100px] rs-hero-float rs-hero-float-d2 sm:top-[120px]"
            icon={<Medal aria-hidden className="size-5" strokeWidth={2.2} />}
            iconClass="bg-gradient-to-br from-rs-navy-800 to-rs-blue-700"
            label={homeHero.floatCards[2].label}
            value={homeHero.floatCards[2].value}
          />
        </div>
      </div>
    </section>
  )
}

function FloatCard({
  className,
  icon,
  iconClass,
  label,
  value,
}: {
  className: string
  icon: ReactNode
  iconClass: string
  label: string
  value: string
}) {
  return (
    <div
      className={[
        'absolute z-[5] flex items-center gap-3 rounded-2xl border border-rs-line bg-white px-4 py-3 shadow-rs',
        className,
      ].join(' ')}
    >
      <div
        className={[
          'flex size-[38px] shrink-0 items-center justify-center rounded-[11px] text-white',
          iconClass,
        ].join(' ')}
      >
        {icon}
      </div>
      <div>
        <small className="block text-[11.5px] font-semibold text-rs-muted">{label}</small>
        <strong className="block text-sm font-extrabold tracking-tight text-rs-ink">{value}</strong>
      </div>
    </div>
  )
}

function LaptopGraphic() {
  return (
    <svg
      aria-hidden
      className="absolute left-0 top-6 z-[2] w-[300px] drop-shadow-[0_40px_60px_rgba(15,40,110,.22)] sm:w-[380px] nav:w-[430px]"
      viewBox="0 0 430 300"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="rs-home-scr" x1="0" y1="0" x2="430" y2="270">
          <stop stopColor="#f6f9ff" />
          <stop offset="1" stopColor="#eaf1ff" />
        </linearGradient>
        <linearGradient id="rs-home-bg1" x1="0" y1="0" x2="0" y2="1">
          <stop stopColor="#1e5eff" />
          <stop offset="1" stopColor="#3a86ff" />
        </linearGradient>
        <linearGradient id="rs-home-bg2" x1="0" y1="0" x2="0" y2="1">
          <stop stopColor="#0d1c40" />
          <stop offset="1" stopColor="#1b48c9" />
        </linearGradient>
      </defs>
      <rect x="35" y="14" width="360" height="232" rx="14" fill="#0d1c40" />
      <rect x="44" y="22" width="342" height="216" rx="8" fill="url(#rs-home-scr)" />
      <rect x="58" y="36" width="120" height="11" rx="5.5" fill="#0d1c40" />
      <rect x="58" y="53" width="80" height="7" rx="3.5" fill="#b9c8ea" />
      <rect x="300" y="34" width="70" height="22" rx="11" fill="url(#rs-home-bg1)" />
      <rect x="58" y="74" width="96" height="44" rx="9" fill="#fff" stroke="#e2ebff" />
      <rect x="68" y="84" width="40" height="9" rx="4" fill="#1e5eff" />
      <rect x="68" y="100" width="60" height="6" rx="3" fill="#c7d6f6" />
      <rect x="166" y="74" width="96" height="44" rx="9" fill="#fff" stroke="#e2ebff" />
      <rect x="176" y="84" width="34" height="9" rx="4" fill="#0d1c40" />
      <rect x="176" y="100" width="64" height="6" rx="3" fill="#c7d6f6" />
      <rect x="274" y="74" width="96" height="44" rx="9" fill="#fff" stroke="#e2ebff" />
      <rect x="284" y="84" width="44" height="9" rx="4" fill="#22c55e" />
      <rect x="284" y="100" width="52" height="6" rx="3" fill="#c7d6f6" />
      <rect x="58" y="130" width="200" height="96" rx="10" fill="#fff" stroke="#e2ebff" />
      <rect x="70" y="142" width="60" height="7" rx="3.5" fill="#0d1c40" />
      <rect x="74" y="200" width="16" height="14" rx="3" fill="#bcd0f7" />
      <rect x="100" y="186" width="16" height="28" rx="3" fill="#7fa8f5" />
      <rect x="126" y="170" width="16" height="44" rx="3" fill="url(#rs-home-bg1)" />
      <rect x="152" y="190" width="16" height="24" rx="3" fill="#7fa8f5" />
      <rect x="178" y="162" width="16" height="52" rx="3" fill="url(#rs-home-bg2)" />
      <rect x="204" y="180" width="16" height="34" rx="3" fill="#bcd0f7" />
      <rect x="266" y="130" width="104" height="96" rx="10" fill="#fff" stroke="#e2ebff" />
      <circle cx="318" cy="180" r="30" fill="none" stroke="#e2ebff" strokeWidth="11" />
      <circle
        cx="318"
        cy="180"
        r="30"
        fill="none"
        stroke="url(#rs-home-bg1)"
        strokeWidth="11"
        strokeDasharray="120 188"
        strokeLinecap="round"
        transform="rotate(-90 318 180)"
      />
      <path d="M18 246h394l16 18H2z" fill="#c3d0ec" />
      <rect x="186" y="250" width="58" height="6" rx="3" fill="#9fb3da" />
    </svg>
  )
}
