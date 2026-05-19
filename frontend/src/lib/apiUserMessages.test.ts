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
  it('maps duplicate MCQ option key errors for question bank save', () => {
    const message = catalogApiUserMessage(
      new ApiError('optionsJson must not contain duplicate option keys', 400),
      'saveQuestionBankQuestion',
    )
    expect(message).toBe('Each answer choice needs a unique label (for example A, B, C).')
    expect(message).not.toContain('optionsJson')
  })

  it('maps duplicate MCQ option key errors for question bank publish', () => {
    const message = catalogApiUserMessage(
      new ApiError('optionsJson must not contain duplicate option keys', 400),
      'publishQuestionBank',
    )
    expect(message).toBe('Each answer choice needs a unique label (for example A, B, C).')
    expect(message).not.toContain('optionsJson')
  })

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

  it('maps module quiz API messages', () => {
    expect(catalogApiUserMessage(new ApiError('Module quiz not available', 404))).toBe(
      'This quiz is not available. It may not be published yet, or you may not have access.',
    )
    expect(catalogApiUserMessage(new ApiError('Module quiz questions could not be loaded', 409))).toBe(
      'This quiz could not be loaded. Refresh the page and try again.',
    )
    expect(catalogApiUserMessage(new ApiError('Module quiz binding is incomplete', 409))).toBe(
      'This quiz could not be loaded. Refresh the page and try again.',
    )
    expect(catalogApiUserMessage(new ApiError('Module quiz submission is incomplete', 409))).toBe(
      'Your answers could not be submitted. Refresh the page and try again.',
    )
    expect(catalogApiUserMessage(new ApiError('Module quiz attempt does not match current question set', 409))).toBe(
      'This attempt is out of date. Refresh the page and try again.',
    )
    expect(catalogApiUserMessage(new ApiError('Answers incomplete', 400), 'submitModuleQuiz')).toBe(
      'Answer every question before submitting.',
    )
  })

  it('keeps plain-language API messages when mapped', () => {
    const err = new ApiError('Module already has a quiz', 409, 'conflict')
    expect(catalogApiUserMessage(err)).toBe('This module already has a quiz attached.')
  })

  it('does not surface request failed status codes, opaque errors, or raw server text', () => {
    expect(catalogApiUserMessage(new ApiError('', 500, 'internal_error'))).toBe(
      'Something went wrong. Please try again.',
    )
    expect(catalogApiUserMessage(new ApiError('boom', 500), 'loadCourse')).toBe(
      'This course could not be loaded. Please try again.',
    )
    expect(catalogApiUserMessage(new ApiError('Internal Server Error', 500), 'loadModuleQuiz')).toBe(
      'This quiz could not be loaded. Refresh the page and try again.',
    )
    expect(catalogApiUserMessage(new ApiError("'title' is required", 400), 'updateCourse')).toBe(
      'Your changes could not be saved. Please try again.',
    )
    expect(catalogApiUserMessage(new ApiError('Unmapped plain failure', 502), 'loadLesson')).toBe(
      'This lesson could not be loaded. Please try again.',
    )
  })

  it('maps checkout session billing codes', () => {
    expect(catalogApiUserMessage(new ApiError('x', 503, 'billing_unconfigured'), 'subscribe')).toBe(
      'Subscriptions are not available right now. Please try again later.',
    )
    expect(catalogApiUserMessage(new ApiError('x', 409, 'already_subscribed'), 'subscribe')).toBe(
      'You already have an active subscription.',
    )
    expect(catalogApiUserMessage(new ApiError('x', 409, 'checkout_in_progress'), 'subscribe')).toBe(
      'A checkout is already in progress. Wait a moment or try again shortly.',
    )
  })

  it('maps subscription manage billing codes', () => {
    expect(catalogApiUserMessage(new ApiError('x', 404, 'not_subscribed'), 'loadSubscription')).toBe(
      'You do not have a subscription to manage yet.',
    )
    expect(catalogApiUserMessage(new ApiError('x', 409, 'already_canceled'), 'cancelSubscription')).toBe(
      'Your subscription is already set to cancel at the end of the billing period.',
    )
    expect(catalogApiUserMessage(new ApiError('x', 409, 'cannot_cancel'), 'cancelSubscription')).toBe(
      'Your subscription cannot be canceled in its current state.',
    )
    expect(
      catalogApiUserMessage(new ApiError('x', 502, 'provider_cancel_failed'), 'cancelSubscription'),
    ).toContain('Try again')
    expect(
      catalogApiUserMessage(new ApiError('x', 502, 'provider_agreement_missing'), 'cancelSubscription'),
    ).toMatch(/contact support/i)
  })

  it('uses context-specific fallbacks for unknown errors', () => {
    expect(catalogApiUserMessage(new Error('network down'), 'loadCourses')).toBe(
      'Your courses could not be loaded. Please try again.',
    )
    expect(catalogApiUserMessage(new Error('Boom'), 'learnRedirect')).toBe(
      'Your course could not be opened. Please try again.',
    )
    expect(catalogApiUserMessage(new Error('network down'), 'retakeModuleQuiz')).toBe(
      'A new quiz attempt could not be started. Refresh the page and try again.',
    )
    expect(catalogApiUserMessage(new Error('network down'), 'attachModuleQuiz')).toBe(
      'The module quiz could not be attached. Please try again.',
    )
    expect(catalogApiUserMessage(new ApiError('Unmapped attach failure', 502), 'attachModuleQuiz')).toBe(
      'The module quiz could not be attached. Please try again.',
    )
    expect(catalogApiUserMessage(new Error('network down'), 'deleteQuestionBankQuestion')).toBe(
      'That question could not be deleted. Please try again.',
    )
    expect(
      catalogApiUserMessage(new ApiError('Unmapped delete failure', 502), 'deleteQuestionBankQuestion'),
    ).toBe('That question could not be deleted. Please try again.')
  })
})
