import {
  BookOpen,
  Clock,
  Medal,
  Users,
  Wrench,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import { Card } from '../../components/ui/Card'
import { Reveal } from '../../components/ui/Reveal'
import { homeTrustItems } from '../../lib/marketing/homeCopy'

const icons: LucideIcon[] = [BookOpen, Wrench, Clock, Medal, Users]

export function HomeTrustBar() {
  return (
    <section className="relative z-[6] px-5 pb-[18px] sm:px-7">
      <div className="mx-auto max-w-wrap">
        <Reveal>
          <Card className="-mt-8 grid grid-cols-2 gap-1.5 rounded-rs-lg p-4 shadow-rs sm:-mt-11 sm:grid-cols-5 sm:gap-0 sm:p-6 sm:px-2.5 sm:py-6">
            {homeTrustItems.map((label, index) => {
              const Icon = icons[index]!
              return (
                <div
                  key={label}
                  className="flex items-center justify-start gap-2.5 px-2.5 py-2 sm:justify-center"
                >
                  <div className="flex size-10 shrink-0 items-center justify-center rounded-[11px] border border-rs-line-2 bg-rs-sky-2">
                    <Icon aria-hidden className="size-5 text-rs-blue" strokeWidth={2} />
                  </div>
                  <span className="text-[13.5px] font-bold leading-tight tracking-tight text-rs-navy">
                    {label}
                  </span>
                </div>
              )
            })}
          </Card>
        </Reveal>
      </div>
    </section>
  )
}
