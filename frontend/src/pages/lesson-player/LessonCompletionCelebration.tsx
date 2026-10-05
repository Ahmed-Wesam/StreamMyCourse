type Props = {
  open: boolean
  title: string
  subtitle: string
  onClose: () => void
}

export function LessonCompletionCelebration({ open, title, subtitle, onClose }: Props) {
  return (
    <div
      className={`completion${open ? ' is-open' : ''}`}
      role="dialog"
      aria-modal="true"
      aria-labelledby="lesson-celebration-title"
      data-testid="lesson-module-celebration"
      hidden={!open}
    >
      <div className="cp-card">
        <button type="button" className="cp-close" aria-label="Close celebration" onClick={onClose}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M18 6 6 18M6 6l12 12" strokeLinecap="round" />
          </svg>
        </button>
        <p className="cp-cong">Module complete</p>
        <h2 id="lesson-celebration-title">{title}</h2>
        <p className="transcript-empty">{subtitle}</p>
        <button type="button" className="btn-complete" onClick={onClose}>
          Continue learning
        </button>
      </div>
    </div>
  )
}
