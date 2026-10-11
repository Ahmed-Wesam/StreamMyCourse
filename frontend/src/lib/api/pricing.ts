/**
 * Instructor pricing API (RS-5 Slice F).
 * Student checkout lives in `./billing.ts`.
 */
import { httpPatch } from './client'

export async function setCoursePrice(
  courseId: string,
  amountMinor: number,
): Promise<{ courseId: string; amountMinor: number; currency: string }> {
  return httpPatch<{ courseId: string; amountMinor: number; currency: string }>(
    `/billing/courses/${courseId}/price`,
    { amountMinor },
  )
}
