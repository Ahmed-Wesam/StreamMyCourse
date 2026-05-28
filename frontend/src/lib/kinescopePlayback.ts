/** Parse Kinescope iframe player TimeUpdate / DurationChange payloads. */
export function parseKinescopeTimePayload(data: unknown): {
  positionSec: number
  durationSec: number
} {
  const payload = data as { currentTime?: number; duration?: number }
  const positionSec = Math.max(0, Math.floor(Number(payload.currentTime) || 0))
  const durationSec = Math.max(0, Math.floor(Number(payload.duration) || 0))
  return { positionSec, durationSec }
}
