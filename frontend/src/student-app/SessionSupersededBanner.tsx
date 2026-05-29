import { X } from 'lucide-react'

type SessionSupersededBannerProps = {
  message: string
  onDismiss: () => void
}

/** Global session-superseded strip (injected under the site header via Layout chromeAlert). */
export function SessionSupersededBanner({ message, onDismiss }: SessionSupersededBannerProps) {
  return (
    <div
      className="flex items-center gap-3 border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 shadow-sm"
      role="alert"
      data-testid="session-superseded-banner"
    >
      <p className="min-w-0 flex-1 text-center">{message}</p>
      <button
        type="button"
        className="shrink-0 rounded-md p-1 text-amber-900/80 transition-colors hover:bg-amber-100 hover:text-amber-950 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-600"
        aria-label="Dismiss sign-in elsewhere notice"
        data-testid="session-superseded-banner-dismiss"
        onClick={onDismiss}
      >
        <X className="h-4 w-4" aria-hidden />
      </button>
    </div>
  )
}
