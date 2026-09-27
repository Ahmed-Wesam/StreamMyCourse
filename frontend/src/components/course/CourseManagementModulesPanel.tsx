import type { CourseModule } from '../../lib/api/types'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Field } from '../ui/Field'

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
    <Card className="mb-6 p-6">
      <h2 className="mb-4 text-xl font-extrabold text-rs-navy">Modules / Sections</h2>

      <div className="mb-6 space-y-3">
        {sortedModules.map((m) => (
          <div key={m.id} className="flex items-start justify-between gap-4 rounded-lg border border-rs-line p-4">
            <div>
              <div className="font-semibold text-rs-navy">{m.title}</div>
              {m.description && <div className="mt-1 text-sm text-rs-body">{m.description}</div>}
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              aria-label="Delete Module"
              className="!text-red-700 hover:!bg-red-50"
              onClick={() => void onDeleteModule(m.id)}
            >
              Delete
            </Button>
          </div>
        ))}
      </div>

      <form onSubmit={onCreateModule} className="rounded-lg border border-rs-line p-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label="Module Title *"
            value={newModuleTitle}
            onChange={(e) => onNewModuleTitleChange(e.target.value)}
            required
          />
          <Field
            label="Description"
            value={newModuleDescription}
            onChange={(e) => onNewModuleDescriptionChange(e.target.value)}
          />
        </div>

        <div className="mt-4 flex justify-end">
          <Button type="submit" size="sm">
            Create Module
          </Button>
        </div>
      </form>
    </Card>
  )
}
