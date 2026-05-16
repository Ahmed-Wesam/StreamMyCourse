import { describe, expect, it } from 'vitest'

import { ApiError } from './api'
import {
  catalogApiUserMessage,
  incompleteLessonPlayerLinkMessage,
  incompleteModuleQuizLinkMessage,
  incompleteQuestionBankStudioLinkMessage,
  incompleteQuestionBanksListLinkMessage,
} from './apiUserMessages'

describe('incomplete route link messages', () => {
  it('does not mention internal ids', () => {
    for (const message of [
      incompleteQuestionBanksListLinkMessage,
      incompleteQuestionBankStudioLinkMessage,
      incompleteModuleQuizLinkMessage,
      incompleteLessonPlayerLinkMessage,
    ]) {
      expect(message.toLowerCase()).not.toMatch(/\bid\b/)
    }
  })
})

describe('catalogApiUserMessage', () => {
  it('maps technical field names to friendly copy', () => {
    expect(catalogApiUserMessage(new ApiError('questionBankId is required', 400, 'bad_request'))).toBe(
      'Choose a question bank to attach.',
    )
    expect(catalogApiUserMessage(new ApiError('N must be at least 1', 400))).toBe(
      'Enter at least one question per attempt.',
    )
    expect(catalogApiUserMessage(new ApiError('promptText must not be empty', 400))).toBe(
      'Enter the question text.',
    )
  })

  it('maps course management errors', () => {
    expect(
      catalogApiUserMessage(new ApiError('Cannot delete the last module in a course', 400, 'last_module_required')),
    ).toContain('last module')
    expect(
      catalogApiUserMessage(
        new ApiError('Course needs at least one ready lesson to publish', 400),
        'publishCourse',
      ),
    ).toBe('Add at least one lesson with a ready video before you can publish this course.')
    expect(catalogApiUserMessage(new ApiError('Module not found', 404), 'deleteModule')).toBe(
      'That module was not found. Refresh the page and try again.',
    )
  })

  it('keeps plain-language API messages when safe', () => {
    const err = new ApiError('Module already has a quiz', 409, 'conflict')
    expect(catalogApiUserMessage(err)).toBe('This module already has a quiz attached.')
  })

  it('does not surface request failed status codes or opaque errors', () => {
    expect(catalogApiUserMessage(new ApiError('', 500, 'internal_error'))).toBe(
      'Something went wrong. Please try again.',
    )
    expect(catalogApiUserMessage(new ApiError('boom', 500), 'loadCourse')).toBe(
      'This course could not be loaded. Please try again.',
    )
    expect(catalogApiUserMessage(new ApiError("'title' is required", 400), 'updateCourse')).toBe(
      'Your changes could not be saved. Please try again.',
    )
  })

  it('uses context-specific fallbacks for unknown errors', () => {
    expect(catalogApiUserMessage(new Error('network down'), 'loadCatalog')).toBe(
      'The course catalog could not be loaded. Please try again.',
    )
    expect(catalogApiUserMessage(new Error('Boom'), 'learnRedirect')).toBe(
      'Your course could not be opened. Please try again.',
    )
  })
})
