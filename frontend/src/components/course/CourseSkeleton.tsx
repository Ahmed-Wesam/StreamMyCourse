export function CourseSkeleton() {
  return (
    <div className="overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm animate-pulse">
      <div className="aspect-video bg-gray-200" />
      <div className="space-y-3 p-5">
        <div className="h-6 w-3/4 rounded bg-gray-200" />
        <div className="h-4 w-full rounded bg-gray-200" />
        <div className="h-4 w-2/3 rounded bg-gray-200" />
        <div className="mt-4 flex justify-between border-t border-gray-100 pt-4">
          <div className="h-5 w-16 rounded bg-gray-200" />
          <div className="h-4 w-20 rounded bg-gray-200" />
        </div>
      </div>
    </div>
  )
}
