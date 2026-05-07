type NavigateFn = (to: string) => void

export function CourseManagementLoadingSkeleton() {
  return (
    <div className="mx-auto max-w-4xl">
      <div className="animate-pulse">
        <div className="mb-8 h-8 w-1/3 rounded bg-gray-200" />
        <div className="mb-6 h-32 rounded-lg bg-gray-200" />
        <div className="h-64 rounded-lg bg-gray-200" />
      </div>
    </div>
  )
}

export function CourseManagementNotFound({ onBack }: { onBack: NavigateFn }) {
  return (
    <div className="mx-auto max-w-4xl text-center" data-testid="course-management-not-found">
      <h1 className="mb-4 text-2xl font-bold text-gray-900">Course not found</h1>
      <button
        type="button"
        onClick={() => onBack('/')}
        className="rounded-lg bg-blue-600 px-6 py-2 text-white transition-colors hover:bg-blue-700"
      >
        Back to Dashboard
      </button>
    </div>
  )
}

export function CourseManagementLoadError({ error, onBack }: { error: string; onBack: NavigateFn }) {
  return (
    <div className="mx-auto max-w-4xl" data-testid="course-management-load-error">
      <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700" role="alert">
        {error}
      </div>
      <button
        type="button"
        onClick={() => onBack('/')}
        className="rounded-lg bg-blue-600 px-6 py-2 text-white transition-colors hover:bg-blue-700"
      >
        Back to Dashboard
      </button>
    </div>
  )
}
