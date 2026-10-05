import type { UserProfile } from './api/types'

export type LessonPlayerPrefs = {
  autoplayNext: boolean
  autoMarkComplete: boolean
  progressCelebrations: boolean
}

const LESSON_PLAYER_PREF_DEFAULTS: LessonPlayerPrefs = {
  autoplayNext: false,
  autoMarkComplete: true,
  progressCelebrations: false,
}

export function resolveLessonPlayerPrefs(profile: UserProfile | null | undefined): LessonPlayerPrefs {
  if (!profile) return { ...LESSON_PLAYER_PREF_DEFAULTS }
  return {
    autoplayNext: typeof profile.autoplayNext === 'boolean' ? profile.autoplayNext : LESSON_PLAYER_PREF_DEFAULTS.autoplayNext,
    autoMarkComplete:
      typeof profile.autoMarkComplete === 'boolean'
        ? profile.autoMarkComplete
        : LESSON_PLAYER_PREF_DEFAULTS.autoMarkComplete,
    progressCelebrations:
      typeof profile.progressCelebrations === 'boolean'
        ? profile.progressCelebrations
        : LESSON_PLAYER_PREF_DEFAULTS.progressCelebrations,
  }
}
