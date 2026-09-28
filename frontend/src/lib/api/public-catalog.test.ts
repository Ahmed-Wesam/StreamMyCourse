/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { listPublishedCourses } from './public-catalog'

describe('listPublishedCourses', () => {
  const originalEnv = import.meta.env.VITE_API_BASE_URL

  beforeEach(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
    vi.clearAllMocks()
  })

  it('maps level, estimatedHours, catalogSkills and ignores detail section objects', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            id: 'rich',
            title: 'Rich Course',
            description: 'Overview',
            status: 'PUBLISHED',
            level: ' Intermediate ',
            estimatedHours: 12,
            catalogSkills: [' SPSS ', '', 'Writing'],
            problem: { heading: 'Problem', body: 'Ignored' },
          },
        ]),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    const courses = await listPublishedCourses()

    expect(courses[0]).toEqual({
      id: 'rich',
      title: 'Rich Course',
      description: 'Overview',
      level: 'Intermediate',
      estimatedHours: 12,
      catalogSkills: ['SPSS', 'Writing'],
    })
    expect(courses[0]).not.toHaveProperty('problem')
  })

  it('drops invalid estimatedHours and empty catalogSkills', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            id: 'sparse',
            title: 'Sparse',
            description: 'x',
            status: 'PUBLISHED',
            estimatedHours: 0,
            catalogSkills: ['  ', ''],
            level: '   ',
          },
        ]),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    const courses = await listPublishedCourses()

    expect(courses[0]).toEqual({
      id: 'sparse',
      title: 'Sparse',
      description: 'x',
    })
  })

  it('maps amountMinor and hasAccess when present', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            id: 'priced',
            title: 'Priced',
            description: 'x',
            status: 'PUBLISHED',
            amountMinor: 4900,
            currency: 'USD',
            hasAccess: true,
          },
        ]),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    const courses = await listPublishedCourses()
    expect(courses[0]).toMatchObject({
      id: 'priced',
      amountMinor: 4900,
      currency: 'USD',
      hasAccess: true,
    })
  })

  it('returns a PUBLISHED course from 200 JSON', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            id: 'c1',
            title: 'Research Design',
            description: 'Foundations',
            status: 'PUBLISHED',
          },
        ]),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    const courses = await listPublishedCourses()

    expect(courses).toEqual([
      { id: 'c1', title: 'Research Design', description: 'Foundations' },
    ])
  })

  it('sends no Authorization header and uses credentials omit', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await listPublishedCourses()

    expect(fetch).toHaveBeenCalledTimes(1)
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toMatch(/\/courses$/)
    expect(init?.method).toBe('GET')
    expect(init?.credentials).toBe('omit')
    expect(init?.cache).toBe('no-store')
    const headers = new Headers(init?.headers as HeadersInit)
    expect(headers.has('Authorization')).toBe(false)
    expect(headers.get('Accept')).toBe('application/json')
  })

  it('keeps https thumbnailUrl and drops non-https values', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            id: 'https-ok',
            title: 'A',
            description: 'a',
            status: 'PUBLISHED',
            thumbnailUrl: 'https://cdn.example/thumb.jpg',
          },
          {
            id: 'http-drop',
            title: 'B',
            description: 'b',
            status: 'PUBLISHED',
            thumbnailUrl: 'http://cdn.example/thumb.jpg',
          },
          {
            id: 'js-drop',
            title: 'C',
            description: 'c',
            status: 'PUBLISHED',
            thumbnailUrl: 'javascript:alert(1)',
          },
          {
            id: 'missing-thumb',
            title: 'D',
            description: 'd',
            status: 'PUBLISHED',
          },
        ]),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    const courses = await listPublishedCourses()

    expect(courses).toEqual([
      {
        id: 'https-ok',
        title: 'A',
        description: 'a',
        thumbnailUrl: 'https://cdn.example/thumb.jpg',
      },
      { id: 'http-drop', title: 'B', description: 'b' },
      { id: 'js-drop', title: 'C', description: 'c' },
      { id: 'missing-thumb', title: 'D', description: 'd' },
    ])
  })

  it('drops published rows that have no id', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify([
          { title: 'Missing id', description: 'x', status: 'PUBLISHED' },
          { id: '   ', title: 'Blank id', description: 'y', status: 'PUBLISHED' },
          { id: 'kept', title: 'Kept', description: 'z', status: 'PUBLISHED' },
        ]),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    const courses = await listPublishedCourses()

    expect(courses).toEqual([{ id: 'kept', title: 'Kept', description: 'z' }])
  })

  it('drops rows whose status is not PUBLISHED', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify([
          { id: 'draft', title: 'Draft', description: 'd', status: 'DRAFT' },
          { id: 'pub', title: 'Live', description: 'l', status: 'PUBLISHED' },
          { id: 'other', title: 'Other', description: 'o', status: 'ARCHIVED' },
        ]),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    const courses = await listPublishedCourses()

    expect(courses).toEqual([{ id: 'pub', title: 'Live', description: 'l' }])
  })

  it('rejects on HTTP 500', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response('server error', { status: 500 }),
    )

    await expect(listPublishedCourses()).rejects.toThrow(Error)
  })

  it('rejects when 200 body is not JSON', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response('not-json', {
        status: 200,
        headers: { 'Content-Type': 'text/plain' },
      }),
    )

    await expect(listPublishedCourses()).rejects.toThrow(Error)
  })

  it('resolves empty array to []', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await expect(listPublishedCourses()).resolves.toEqual([])
  })
})
