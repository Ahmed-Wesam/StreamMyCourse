import { ApiError } from './api'

/**
 * User-facing copy for catalog API failures (question banks, module quiz, etc.).
 */
export function catalogApiUserMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 404) {
      return 'That item was not found or you no longer have access to it.'
    }
    if (err.status === 409) {
      return 'This action conflicts with the current state of the bank or quiz. Refresh the page and try again.'
    }
    if (err.message.trim()) return err.message.trim()
    return `Request failed (${err.status}).`
  }
  if (err instanceof Error && err.message.trim()) return err.message.trim()
  return 'Something went wrong. Please try again.'
}

/**
 * User-facing copy for question bank studio flows (load, CRUD, publish).
 */
export function questionBankUserMessage(err: unknown): string {
  return catalogApiUserMessage(err)
}
