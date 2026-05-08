import type { CourseModule } from '../../lib/api'

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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-md w-full p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Add New Lesson</h2>
        <form onSubmit={onSubmit}>
          <div className="mb-4">
            <label htmlFor="lesson-title" className="block text-sm font-medium text-gray-700 mb-1">
              Lesson Title *
            </label>
            <input
              id="lesson-title"
              type="text"
              value={newLessonTitle}
              onChange={(e) => onNewLessonTitleChange(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="e.g., Introduction"
              required
            />
          </div>

          {sortedModules.length > 0 && (
            <div className="mb-4">
              <label htmlFor="lesson-module" className="block text-sm font-medium text-gray-700 mb-1">
                Module
              </label>
              <select
                id="lesson-module"
                value={selectedModuleId}
                onChange={(e) => onSelectedModuleIdChange(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {sortedModules.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.title}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div className="mb-4">
            <label htmlFor="lesson-video" className="block text-sm font-medium text-gray-700 mb-1">
              Video File *
            </label>
            <input
              id="lesson-video"
              type="file"
              accept="video/*"
              onChange={onFileChange}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
            {selectedFile && (
              <p className="text-sm text-gray-600 mt-2">
                Selected: {selectedFile.name} ({Math.round(selectedFile.size / 1024 / 1024)}MB)
              </p>
            )}
          </div>

          {uploading && (
            <div className="mb-4">
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>Uploading...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onCancel}
              disabled={uploading}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={uploading || !newLessonTitle.trim() || !selectedFile}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {uploading ? 'Uploading...' : 'Add Lesson'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
