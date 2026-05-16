/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const fetchAuthSessionMock = vi.hoisted(() => vi.fn())

vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: (...args: unknown[]) => fetchAuthSessionMock(...args),
}))

vi.mock('./auth', () => ({
  isAuthConfigured: () => true,
}))

import {
  createModuleQuiz,
  createQuestionBank,
  createQuestionBankQuestion,
  deleteQuestionBankQuestion,
  listCourseModuleQuizzes,
  listCourseQuestionBanks,
  listQuestionBankQuestions,
  publishQuestionBank,
  updateQuestionBankName,
  updateQuestionBankQuestion,
} from './api'

/** IDs with `/` so paths must use encodeURIComponent segments. */
const COURSE_ID = 'c/1'
const BANK_ID = 'b/2'
const QUESTION_ID = 'q/3'
const MODULE_ID = 'm/4'

const enc = {
  course: encodeURIComponent(COURSE_ID),
  bank: encodeURIComponent(BANK_ID),
  question: encodeURIComponent(QUESTION_ID),
  module: encodeURIComponent(MODULE_ID),
}

function happyPathQuestionBankResponse(url: string, method: string): Response {
  const json = (body: unknown, status = 200) =>
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    })

  const routes: Array<{
    method: string
    match: (u: string) => boolean
    body: unknown
    status?: number
  }> = [
    { method: 'GET', match: (u) => u.includes(`/courses/${enc.course}/module-quizzes`), body: [] },
    {
      method: 'GET',
      match: (u) => u.includes(`/courses/${enc.course}/question-banks`) && u.includes('/questions'),
      body: [],
    },
    {
      method: 'GET',
      match: (u) => u.includes(`/courses/${enc.course}/question-banks`) && !u.includes('/questions'),
      body: [],
    },
    {
      method: 'POST',
      match: (u) => u.includes(`/courses/${enc.course}/question-banks/${enc.bank}/publish`),
      body: { status: 'PUBLISHED' },
    },
    {
      method: 'POST',
      match: (u) => u.includes(`/courses/${enc.course}/question-banks/${enc.bank}/questions`),
      body: { questionId: 'new-q' },
      status: 201,
    },
    {
      method: 'POST',
      match: (u) =>
        u.includes(`/courses/${enc.course}/question-banks`) &&
        !u.includes('/questions') &&
        !u.includes('/publish'),
      body: { questionBankId: 'new-bank', name: 'Chapter 1 quiz' },
      status: 201,
    },
    {
      method: 'PATCH',
      match: (u) =>
        u.includes(`/courses/${enc.course}/question-banks/${enc.bank}`) &&
        !u.includes('/questions'),
      body: { questionBankId: BANK_ID, name: 'Renamed bank' },
    },
    {
      method: 'PATCH',
      match: (u) => u.includes(`/courses/${enc.course}/question-banks/${enc.bank}/questions/${enc.question}`),
      body: { status: 'updated' },
    },
    {
      method: 'DELETE',
      match: (u) => u.includes(`/courses/${enc.course}/question-banks/${enc.bank}/questions/${enc.question}`),
      body: { status: 'deleted' },
    },
    {
      method: 'POST',
      match: (u) => u.includes(`/courses/${enc.course}/modules/${enc.module}/quiz`),
      body: { quizId: 'quiz-1' },
    },
  ]

  for (const r of routes) {
    if (r.method === method && r.match(url)) {
      return json(r.body, r.status ?? 200)
    }
  }
  return json({ error: 'unhandled', url, method }, 500)
}

describe('question banks & module quiz publisher API (happy paths)', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL

  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = typeof input === 'string' ? input : input.toString()
        const method = init?.method ?? 'GET'
        return happyPathQuestionBankResponse(url, method)
      }),
    )
    fetchAuthSessionMock.mockResolvedValue({ tokens: { idToken: 't' } })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
    vi.clearAllMocks()
  })

  it('listCourseQuestionBanks GETs encoded course segment', async () => {
    await listCourseQuestionBanks(COURSE_ID)
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain(`/courses/${enc.course}/question-banks`)
    expect(init?.method).toBeUndefined()
  })

  it('listCourseModuleQuizzes GETs encoded course segment', async () => {
    await listCourseModuleQuizzes(COURSE_ID)
    const [url] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain(`/courses/${enc.course}/module-quizzes`)
  })

  it('listQuestionBankQuestions GETs encoded course and bank segments', async () => {
    await listQuestionBankQuestions(COURSE_ID, BANK_ID)
    const [url] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain(`/courses/${enc.course}/question-banks/${enc.bank}/questions`)
  })

  it('createQuestionBank POSTs name to encoded path and returns it', async () => {
    const result = await createQuestionBank(COURSE_ID, { name: 'Chapter 1 quiz' })
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain(`/courses/${enc.course}/question-banks`)
    expect(String(url)).not.toContain(`${enc.course}/question-banks/${enc.bank}`)
    expect(init?.method).toBe('POST')
    expect(JSON.parse((init?.body as string) ?? '{}')).toEqual({ name: 'Chapter 1 quiz' })
    expect(result).toEqual({ questionBankId: 'new-bank', name: 'Chapter 1 quiz' })
  })

  it('updateQuestionBankName PATCHes name to encoded bank path and returns it', async () => {
    const result = await updateQuestionBankName(COURSE_ID, BANK_ID, { name: 'Renamed bank' })
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain(`/courses/${enc.course}/question-banks/${enc.bank}`)
    expect(String(url)).not.toContain('/questions')
    expect(init?.method).toBe('PATCH')
    expect(JSON.parse((init?.body as string) ?? '{}')).toEqual({ name: 'Renamed bank' })
    expect(result).toEqual({ questionBankId: BANK_ID, name: 'Renamed bank' })
  })

  it('createQuestionBankQuestion POSTs JSON body with encoded segments', async () => {
    const body = {
      promptText: 'Q?',
      optionsJson: [
        { key: 'a', text: 'A' },
        { key: 'b', text: 'B' },
      ],
      correctOptionKey: 'a',
    }
    await createQuestionBankQuestion(COURSE_ID, BANK_ID, body)
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain(`/courses/${enc.course}/question-banks/${enc.bank}/questions`)
    expect(init?.method).toBe('POST')
    expect(JSON.parse((init?.body as string) ?? '{}')).toEqual(body)
  })

  it('updateQuestionBankQuestion PATCHes JSON body', async () => {
    await updateQuestionBankQuestion(COURSE_ID, BANK_ID, QUESTION_ID, { promptText: 'Updated' })
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain(`/courses/${enc.course}/question-banks/${enc.bank}/questions/${enc.question}`)
    expect(init?.method).toBe('PATCH')
    expect(JSON.parse((init?.body as string) ?? '{}')).toEqual({ promptText: 'Updated' })
  })

  it('deleteQuestionBankQuestion DELETEs encoded question path', async () => {
    await deleteQuestionBankQuestion(COURSE_ID, BANK_ID, QUESTION_ID)
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain(`/courses/${enc.course}/question-banks/${enc.bank}/questions/${enc.question}`)
    expect(init?.method).toBe('DELETE')
  })

  it('publishQuestionBank POSTs n and moduleId', async () => {
    await publishQuestionBank(COURSE_ID, BANK_ID, { n: 3, moduleId: MODULE_ID })
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain(`/courses/${enc.course}/question-banks/${enc.bank}/publish`)
    expect(init?.method).toBe('POST')
    expect(JSON.parse((init?.body as string) ?? '{}')).toEqual({ n: 3, moduleId: MODULE_ID })
  })

  it('createModuleQuiz POSTs questionBankId with encoded module path', async () => {
    await createModuleQuiz(COURSE_ID, MODULE_ID, { questionBankId: BANK_ID })
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain(`/courses/${enc.course}/modules/${enc.module}/quiz`)
    expect(init?.method).toBe('POST')
    expect(JSON.parse((init?.body as string) ?? '{}')).toEqual({ questionBankId: BANK_ID })
  })
})

describe('question banks API errors (ApiError)', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL

  beforeEach(() => {
    fetchAuthSessionMock.mockResolvedValue({ tokens: { idToken: 't' } })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
    vi.clearAllMocks()
  })

  it('listCourseQuestionBanks maps 404 JSON message and code', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ message: '  missing course  ', code: '  not_found  ' }), {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    await expect(listCourseQuestionBanks(COURSE_ID)).rejects.toMatchObject({
      name: 'ApiError',
      status: 404,
      message: 'missing course',
      code: 'not_found',
    })
  })

  it('updateQuestionBankQuestion maps 409 JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ message: 'Cannot edit published', code: 'conflict' }), {
          status: 409,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    await expect(
      updateQuestionBankQuestion(COURSE_ID, BANK_ID, QUESTION_ID, { promptText: 'x' }),
    ).rejects.toMatchObject({
      name: 'ApiError',
      status: 409,
      message: 'Cannot edit published',
      code: 'conflict',
    })
  })

  it('createModuleQuiz maps 400 bad_request', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ message: 'Invalid body', code: 'bad_request' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    await expect(createModuleQuiz(COURSE_ID, MODULE_ID, { questionBankId: 'x' })).rejects.toMatchObject({
      name: 'ApiError',
      status: 400,
      message: 'Invalid body',
      code: 'bad_request',
    })
  })

  it('deleteQuestionBankQuestion maps 409 JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ message: 'Published row', code: 'conflict' }), {
          status: 409,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    await expect(deleteQuestionBankQuestion(COURSE_ID, BANK_ID, QUESTION_ID)).rejects.toMatchObject({
      name: 'ApiError',
      status: 409,
      message: 'Published row',
      code: 'conflict',
    })
  })
})
