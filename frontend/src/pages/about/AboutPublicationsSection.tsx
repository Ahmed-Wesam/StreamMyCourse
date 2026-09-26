import { Reveal } from '../../components/ui/Reveal'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { aboutPublications } from '../../lib/marketing/aboutCopy'

const DOI_REL = 'noopener noreferrer'

export function AboutPublicationsSection() {
  return (
    <section id="publications" className="scroll-mt-24 px-5 py-20 sm:px-7">
      <div className="mx-auto max-w-wrap">
        <Reveal>
          <div className="mb-10">
            <SectionHeader
              kicker={aboutPublications.kicker}
              title={aboutPublications.title}
              lead={aboutPublications.lead}
            />
          </div>
        </Reveal>

        <Reveal>
          <div className="grid grid-cols-1 gap-[18px] sm:grid-cols-2">
            {aboutPublications.featured.map((pub) => (
              <a
                key={pub.href}
                href={pub.href}
                target="_blank"
                rel={DOI_REL}
                className="block rounded-2xl border border-rs-line border-l-4 border-l-rs-blue bg-white px-6 py-[22px] shadow-rs-sm transition duration-300 ease-rs hover:-translate-y-1 hover:shadow-rs"
              >
                <span className="mb-3 inline-block whitespace-nowrap rounded-full bg-rs-sky px-2.5 py-1 text-[11.5px] font-extrabold uppercase tracking-wider text-rs-blue">
                  {pub.venue}
                </span>
                <p className="text-base font-bold leading-snug text-rs-ink">{pub.title}</p>
              </a>
            ))}
          </div>
        </Reveal>

        <Reveal>
          <details className="mt-7 rounded-2xl border border-rs-line bg-white shadow-rs-sm">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-2.5 px-6 py-[18px] text-[15.5px] font-extrabold text-rs-navy [&::-webkit-details-marker]:hidden">
              <span>{aboutPublications.fullListSummary}</span>
              <span aria-hidden className="text-rs-muted">
                ▾
              </span>
            </summary>
            <div className="px-[26px] pb-[26px] pt-1">
              <p className="mb-3.5 mt-1.5 text-xs font-extrabold uppercase tracking-widest text-rs-muted">
                {aboutPublications.fullListHeading}
              </p>
              <ol className="flex list-decimal flex-col gap-4 pl-5">
                {aboutPublications.fullList.map((entry) => (
                  <li key={entry.href + entry.doiLabel} className="text-[14.5px] leading-relaxed text-rs-body">
                    {entry.authorsBefore}
                    <strong className="font-bold text-rs-ink">{entry.highlight}</strong>
                    {entry.authorsAfter}
                    {entry.citation}
                    <a
                      href={entry.href}
                      target="_blank"
                      rel={DOI_REL}
                      className="font-semibold text-rs-blue"
                    >
                      {entry.doiLabel}
                    </a>
                  </li>
                ))}
              </ol>
            </div>
          </details>
        </Reveal>
      </div>
    </section>
  )
}
