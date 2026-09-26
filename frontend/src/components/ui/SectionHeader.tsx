import { Kicker } from './Kicker'

type SectionHeaderProps = {
  kicker?: string
  title: string
  lead?: string
  level?: 1 | 2 | 3
  align?: 'center' | 'start'
}

export function SectionHeader({
  kicker,
  title,
  lead,
  level = 2,
  align = 'center',
}: SectionHeaderProps) {
  const HeadingTag = (`h${level}` as 'h1' | 'h2' | 'h3')
  const isCenter = align === 'center'

  return (
    <div className={isCenter ? 'text-center' : 'text-start'}>
      {kicker ? (
        <span className={isCenter ? undefined : '[&>span]:text-start'}>
          <Kicker>{kicker}</Kicker>
        </span>
      ) : null}
      <HeadingTag
        className={[
          'text-[clamp(28px,4vw,44px)] font-extrabold tracking-tight leading-[1.12] text-rs-ink',
          isCenter ? 'text-center' : 'text-start',
        ].join(' ')}
      >
        {title}
      </HeadingTag>
      {lead ? (
        <p
          className={[
            'text-rs-body text-lg leading-relaxed mt-4',
            isCenter ? 'text-center max-w-[620px] mx-auto' : 'text-start max-w-[620px]',
          ].join(' ')}
        >
          {lead}
        </p>
      ) : null}
    </div>
  )
}
