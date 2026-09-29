import { Button } from '../../components/ui/Button'
import type {
  CertificateInProgressFixture,
  CertificateProfileIncompleteFixture,
} from './certificateFixture'

export type CertificateProgressCardProps =
  | { progress: CertificateInProgressFixture; incomplete?: undefined }
  | { incomplete: CertificateProfileIncompleteFixture; progress?: undefined }

export function CertificateProgressCard(props: CertificateProgressCardProps) {
  if (props.incomplete) {
    const { incomplete } = props
    return (
      <article className="rounded-[22px] border-[1.5px] border-dashed border-rs-line bg-rs-sky-2 px-7 py-[38px] text-center shadow-rs-sm">
        <p className="mb-2 text-[10.5px] font-extrabold uppercase tracking-[0.2em] text-[#c0cce0]">
          Certificate of Completion
        </p>
        <h3 className="mb-2.5 text-[19px] font-extrabold leading-snug tracking-tight text-rs-navy">
          {incomplete.courseTitle}
        </h3>
        <p className="mb-5 text-[14.5px] font-semibold leading-relaxed text-rs-body">{incomplete.message}</p>
        <Button to={incomplete.href} variant="primary" className="w-full justify-center text-[14.5px]">
          Complete Profile
        </Button>
      </article>
    )
  }

  const { progress } = props
  const pct = progress.totalCount > 0 ? Math.round((progress.passedCount / progress.totalCount) * 100) : 0

  return (
    <article className="rounded-[22px] border-[1.5px] border-dashed border-rs-line bg-rs-sky-2 px-7 py-[38px] text-center shadow-rs-sm">
      <div className="mx-auto mb-[18px] flex size-[72px] items-center justify-center rounded-full border-2 border-dashed border-[#ccd5eb] bg-[#eef2fb] text-[#a9b4cd]">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="size-7" aria-hidden>
          <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
          <rect x="9" y="3" width="6" height="4" rx="1" />
        </svg>
      </div>
      <p className="mb-2 text-[10.5px] font-extrabold uppercase tracking-[0.2em] text-[#c0cce0]">
        Certificate of Completion
      </p>
      <h3 className="mb-2.5 text-[19px] font-extrabold leading-snug tracking-tight text-rs-navy">
        {progress.courseTitle}
      </h3>
      <span className="mb-4 inline-flex items-center gap-1.5 rounded-full border border-[#cfdcfb] bg-rs-sky px-3 py-1 text-[11.5px] font-extrabold uppercase tracking-wider text-rs-blue">
        In Progress
      </span>
      <div className="mb-5">
        <div className="mb-1.5 flex justify-between text-xs font-bold text-rs-navy">
          <span>
            {progress.passedCount} of {progress.totalCount}
          </span>
          <b className="text-rs-blue">{pct}%</b>
        </div>
        <div className="h-[7px] overflow-hidden rounded-[5px] bg-rs-line-2">
          <i
            className="block h-full rounded-[5px] bg-rs-grad-cta"
            style={{ width: `${pct}%` }}
            aria-hidden
          />
        </div>
      </div>
    </article>
  )
}
