import { sessionSupersededUserMessage } from './session-superseded-message'
import {
  clearSessionSupersededBanner,
  persistSessionSupersededBanner,
  readSessionSupersededBanner,
} from './session-superseded-banner-storage'

let supersededFlag = false

/** Idempotent: set in-memory flag and persist banner once. */
export function enterSupersededState(): void {
  supersededFlag = true
  if (!readSessionSupersededBanner()) {
    persistSessionSupersededBanner(sessionSupersededUserMessage)
  }
}

/** Restore in-memory flag from persisted banner without fan-out to listeners. */
export function syncSupersededFromStorage(): void {
  if (readSessionSupersededBanner()) {
    supersededFlag = true
  }
}

export function isStudentSessionSuperseded(): boolean {
  return supersededFlag || readSessionSupersededBanner() !== null
}

export function exitSupersededState(): void {
  supersededFlag = false
  clearSessionSupersededBanner()
}

/** Test helper only. */
export function resetSupersededFlagForTests(): void {
  supersededFlag = false
}
