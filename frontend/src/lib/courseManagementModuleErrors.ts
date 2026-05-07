import { isLastModuleDeleteError, isMediaCleanupUnavailableError } from './api'

/** User-visible message for failed module delete, or null to use generic fallback. */
export function moduleDeleteFailureMessage(err: unknown): string | null {
  if (isLastModuleDeleteError(err)) {
    return "You can't delete the last module — every course needs at least one section."
  }
  if (isMediaCleanupUnavailableError(err)) {
    return "Media cleanup is not configured for this environment, so modules with uploaded videos can't be deleted right now. Contact an admin."
  }
  return null
}
