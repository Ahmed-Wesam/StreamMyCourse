import { Button } from '../ui/Button'

type NavigateFn = (to: string) => void

const pageShellClass =
  'mx-auto w-full max-w-5xl px-4 py-8 text-rs-ink sm:px-6 lg:px-8'

export function CourseManagementLoadingSkeleton() {
  return (
    <div className={pageShellClass}>
      <div className="animate-pulse">
        <div className="mb-8 h-8 w-1/3 rounded bg-rs-sky-2" />
        <div className="mb-6 h-32 rounded-lg bg-rs-sky-2" />
        <div className="h-64 rounded-lg bg-rs-sky-2" />
      </div>
    </div>
  )
}

export function CourseManagementNotFound({ onBack }: { onBack: NavigateFn }) {
  return (
    <div className={`${pageShellClass} text-center`} data-testid="course-management-not-found">
      <h1 className="mb-4 text-2xl font-extrabold text-rs-navy">Course not found</h1>
      <Button type="button" onClick={() => onBack('/')}>
        Back to Dashboard
      </Button>
    </div>
  )
}

export function CourseManagementLoadError({ error, onBack }: { error: string; onBack: NavigateFn }) {
  return (
    <div className={pageShellClass} data-testid="course-management-load-error">
      <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700" role="alert">
        {error}
      </div>
      <Button type="button" onClick={() => onBack('/')}>
        Back to Dashboard
      </Button>
    </div>
  )
}
