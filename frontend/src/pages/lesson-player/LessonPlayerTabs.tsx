import { useId, useState } from 'react'

const LESSON_PLAYER_TAB_IDS = [
  'overview',
  'resources',
  'downloads',
  'notes',
  'assignments',
] as const

type LessonPlayerTabId = (typeof LESSON_PLAYER_TAB_IDS)[number]

const TAB_LABELS: Record<LessonPlayerTabId, string> = {
  overview: 'Overview',
  resources: 'Resources',
  downloads: 'Downloads',
  notes: 'Notes',
  assignments: 'Assignments',
}

const PLACEHOLDER_MESSAGE = 'Not available yet.'

export function LessonPlayerTabs({
  courseDescription,
  activeModuleLabel,
  activeLessonTitle,
}: {
  courseDescription?: string
  activeModuleLabel: string
  activeLessonTitle: string
}) {
  const [activeTab, setActiveTab] = useState<LessonPlayerTabId>('overview')
  const baseId = useId()

  const lessonContext = [activeModuleLabel, activeLessonTitle].filter(Boolean).join(' · ')
  const trimmedDescription = courseDescription?.trim() ?? ''

  return (
    <div className="mt-5">
      <div
        role="tablist"
        aria-label="Lesson content"
        className="flex gap-1 overflow-x-auto border-b border-rs-line pb-px [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {LESSON_PLAYER_TAB_IDS.map((tabId) => {
          const selected = activeTab === tabId
          return (
            <button
              key={tabId}
              type="button"
              role="tab"
              id={`${baseId}-tab-${tabId}`}
              aria-selected={selected}
              aria-controls={`${baseId}-panel-${tabId}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => setActiveTab(tabId)}
              className={`shrink-0 rounded-t-lg px-3 py-2.5 text-sm font-semibold transition-colors ${
                selected
                  ? 'border border-b-0 border-rs-line bg-white text-rs-navy'
                  : 'text-rs-muted hover:bg-rs-sky-2/80 hover:text-rs-navy'
              }`}
            >
              {TAB_LABELS[tabId]}
            </button>
          )
        })}
      </div>

      {LESSON_PLAYER_TAB_IDS.map((tabId) => {
        const selected = activeTab === tabId
        return (
          <div
            key={tabId}
            role="tabpanel"
            id={`${baseId}-panel-${tabId}`}
            aria-labelledby={`${baseId}-tab-${tabId}`}
            hidden={!selected}
            className="rounded-b-rs-sm border border-t-0 border-rs-line bg-white px-4 py-5 shadow-rs-sm"
            data-testid={selected ? 'lesson-player-tab-panel' : undefined}
          >
            {tabId === 'overview' ? (
              <div className="space-y-3 text-sm leading-relaxed text-rs-body">
                {trimmedDescription ? <p>{trimmedDescription}</p> : null}
                {lessonContext ? (
                  <p className={trimmedDescription ? 'text-rs-muted' : undefined}>{lessonContext}</p>
                ) : null}
              </div>
            ) : (
              <p
                className="text-sm text-rs-muted"
                data-testid={selected ? 'lesson-player-tab-placeholder' : undefined}
              >
                {PLACEHOLDER_MESSAGE}
              </p>
            )}
          </div>
        )
      })}
    </div>
  )
}
