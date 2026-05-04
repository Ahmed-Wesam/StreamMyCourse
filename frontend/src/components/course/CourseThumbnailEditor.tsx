import type { Course } from '../../lib/api'

type CourseThumbnailEditorProps = {
  course: Course
  thumbFile: File | null
  thumbUploading: boolean
  onThumbFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  onUpload: () => void
}

export function CourseThumbnailEditor({
  course,
  thumbFile,
  thumbUploading,
  onThumbFileChange,
  onUpload,
}: CourseThumbnailEditorProps) {
  return (
    <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-xl font-semibold text-gray-900">Course thumbnail</h2>
      <p className="mb-4 text-sm text-gray-600">
        Square or 16:9 images work best. Shown on the catalog and instructor dashboard.
      </p>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
        <div className="aspect-video w-full max-w-xs overflow-hidden rounded-lg border border-gray-200 bg-slate-100">
          {course.thumbnailUrl ? (
            <img src={course.thumbnailUrl} alt="" className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-gray-500">No thumbnail</div>
          )}
        </div>
        <div className="flex-1 space-y-3">
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={onThumbFileChange}
            className="w-full text-sm text-gray-700 file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-gray-800 hover:file:bg-slate-200"
          />
          {thumbFile && (
            <p className="text-sm text-gray-600">
              Selected: {thumbFile.name} ({Math.round(thumbFile.size / 1024)} KB)
            </p>
          )}
          <button
            type="button"
            onClick={onUpload}
            disabled={thumbUploading || !thumbFile}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {thumbUploading ? 'Uploading…' : 'Upload thumbnail'}
          </button>
        </div>
      </div>
    </div>
  )
}
