import { Reveal } from '../../components/ui/Reveal'
import { aboutStory } from '../../lib/marketing/aboutCopy'

export function AboutStorySection() {
  return (
    <section id="story" className="scroll-mt-24 px-5 py-20 sm:px-7">
      <div className="mx-auto max-w-[760px]">
        <Reveal>
          <h2 className="text-[clamp(26px,3.5vw,38px)] font-extrabold leading-[1.14] tracking-tight text-rs-ink">
            {aboutStory.titleBefore}
            <br />
            <span className="bg-rs-grad-cta bg-clip-text text-transparent">
              {aboutStory.titleHighlight}
            </span>
          </h2>
          {aboutStory.paragraphs.map((paragraph) => (
            <p key={paragraph.slice(0, 40)} className="mt-[18px] text-base leading-relaxed text-rs-body">
              {paragraph}
            </p>
          ))}
          <blockquote className="my-6 rounded-r-[14px] border-l-4 border-rs-blue bg-rs-sky-2 px-[22px] py-4">
            <p className="text-[17.5px] font-bold italic leading-snug text-rs-navy">
              {aboutStory.pullQuote}
            </p>
          </blockquote>
          <p className="text-base leading-relaxed text-rs-body">{aboutStory.closing}</p>
        </Reveal>
      </div>
    </section>
  )
}
