import { useEffect } from 'react'

import { subscribeSessionSuperseded } from './student-session-superseded'
import {
  readSessionSupersededBanner,
  subscribeSessionSupersededDismiss,
} from './session-superseded-banner'

/** Stop lesson playback when the global session-superseded flow runs. */
export function useRevokeLessonPlaybackOnSessionSuperseded(revoke: () => void): void {
  useEffect(() => {
    if (readSessionSupersededBanner()) revoke()
  }, [revoke])

  useEffect(() => subscribeSessionSuperseded(revoke), [revoke])

  useEffect(() => subscribeSessionSupersededDismiss(revoke), [revoke])
}
