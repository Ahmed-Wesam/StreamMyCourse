import type { Course } from '../../lib/api/types'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'

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
    <Card className="mb-6 p-6">
      <h2 className="mb-4 text-xl font-extrabold text-rs-navy">Course thumbnail</h2>
      <p className="mb-4 text-sm text-rs-body">
        Square or 16:9 images work best. Shown on the catalog and instructor dashboard.
      </p>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
        <div className="aspect-video w-full max-w-xs overflow-hidden rounded-lg border border-rs-line bg-rs-sky-2">
          {course.thumbnailUrl ? (
            <img src={course.thumbnailUrl} alt="" className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-rs-muted">No thumbnail</div>
          )}
        </div>
        <div className="flex-1 space-y-3">
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={onThumbFileChange}
            className="w-full text-sm text-rs-body file:mr-3 file:rounded-md file:border-0 file:bg-rs-sky-2 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-rs-navy hover:file:bg-rs-sky"
          />
          {thumbFile && (
            <p className="text-sm text-rs-body">
              Selected: {thumbFile.name} ({Math.round(thumbFile.size / 1024)} KB)
            </p>
          )}
          <Button type="button" size="sm" disabled={thumbUploading || !thumbFile} onClick={onUpload}>
            {thumbUploading ? 'Uploading…' : 'Upload thumbnail'}
          </Button>
        </div>
      </div>
    </Card>
  )
}
