import type { CourseModule } from '../../lib/api'

type Props = {
  sortedModules: CourseModule[]
  newModuleTitle: string
  newModuleDescription: string
  onNewModuleTitleChange: (v: string) => void
  onNewModuleDescriptionChange: (v: string) => void
  onCreateModule: (e: React.FormEvent) => void
  onDeleteModule: (moduleId: string) => void
}

export function CourseManagementModulesPanel({
  sortedModules,
  newModuleTitle,
  newModuleDescription,
  onNewModuleTitleChange,
  onNewModuleDescriptionChange,
  onCreateModule,
  onDeleteModule,
}: Props) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">Modules / Sections</h2>

      <div className="space-y-3 mb-6">
        {sortedModules.map((m) => (
          <div key={m.id} className="flex items-start justify-between gap-4 rounded-lg border border-gray-200 p-4">
            <div>
              <div className="font-medium text-gray-900">{m.title}</div>
              {m.description && <div className="mt-1 text-sm text-gray-600">{m.description}</div>}
            </div>
            <button
              type="button"
              aria-label="Delete Module"
              onClick={() => void onDeleteModule(m.id)}
              className="text-red-600 hover:text-red-800 text-sm px-3 py-1 hover:bg-red-50 rounded transition-colors"
            >
              Delete
            </button>
          </div>
        ))}
      </div>

      <form onSubmit={onCreateModule} className="rounded-lg border border-gray-200 p-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="new-module-title" className="block text-sm font-medium text-gray-700 mb-1">
              Module Title *
            </label>
            <input
              id="new-module-title"
              type="text"
              value={newModuleTitle}
              onChange={(e) => onNewModuleTitleChange(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>
          <div>
            <label htmlFor="new-module-description" className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <input
              id="new-module-description"
              type="text"
              value={newModuleDescription}
              onChange={(e) => onNewModuleDescriptionChange(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        <div className="mt-4 flex justify-end">
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            Create Module
          </button>
        </div>
      </form>
    </div>
  )
}
