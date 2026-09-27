import type { CourseModule } from '../../lib/api/types'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Field } from '../ui/Field'

type Props = {
  sortedModules: CourseModule[]
  newLessonTitle: string
  selectedModuleId: string
  selectedFile: File | null
  uploading: boolean
  uploadProgress: number
  onNewLessonTitleChange: (v: string) => void
  onSelectedModuleIdChange: (v: string) => void
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  onSubmit: (e: React.FormEvent) => void
  onCancel: () => void
}

export function CourseManagementAddLessonModal({
  sortedModules,
  newLessonTitle,
  selectedModuleId,
  selectedFile,
  uploading,
  uploadProgress,
  onNewLessonTitleChange,
  onSelectedModuleIdChange,
  onFileChange,
  onSubmit,
  onCancel,
}: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <Card className="max-w-md w-full p-6">
        <h2 className="mb-4 text-2xl font-extrabold text-rs-navy">Add New Lesson</h2>
        <form onSubmit={onSubmit}>
          <Field
            label="Lesson Title *"
            value={newLessonTitle}
            onChange={(e) => onNewLessonTitleChange(e.target.value)}
            placeholder="e.g., Introduction"
            required
          />

          {sortedModules.length > 0 && (
            <Field label="Module">
              <select
                value={selectedModuleId}
                onChange={(e) => onSelectedModuleIdChange(e.target.value)}
              >
                {sortedModules.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.title}
                  </option>
                ))}
              </select>
            </Field>
          )}
          <Field label="Video File *">
            <input type="file" accept="video/*" onChange={onFileChange} required />
          </Field>
          {selectedFile && (
            <p className="-mt-2 mb-4 text-sm text-rs-body">
              Selected: {selectedFile.name} ({Math.round(selectedFile.size / 1024 / 1024)}MB)
            </p>
          )}

          {uploading && (
            <div className="mb-4">
              <div className="mb-1 flex justify-between text-sm text-rs-body">
                <span>Uploading...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="h-2 w-full rounded-full bg-rs-sky-2">
                <div
                  className="h-2 rounded-full bg-rs-blue transition-all"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <Button type="button" variant="ghost" className="flex-1" onClick={onCancel} disabled={uploading}>
              Cancel
            </Button>
            <Button
              type="submit"
              className="flex-1"
              disabled={uploading || !newLessonTitle.trim() || !selectedFile}
            >
              {uploading ? 'Uploading...' : 'Add Lesson'}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}
