/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { getPublicCertificate } from './public-certificates'

describe('getPublicCertificate', () => {
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

  it('fetches without an Authorization header', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          credentialId: 'RS-A1B7F3-2026-9C2E10B4D8',
          status: 'valid',
          studentName: 'Ada Lovelace',
          courseTitle: 'Research Methodology',
          issueDate: 'September 2026',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    await getPublicCertificate('RS-A1B7F3-2026-9C2E10B4D8')

    expect(fetch).toHaveBeenCalledTimes(1)
    const [, init] = vi.mocked(fetch).mock.calls[0] ?? []
    expect(init?.credentials).toBe('omit')
    const headers = new Headers(init?.headers)
    expect(headers.has('Authorization')).toBe(false)
  })

  it('maps 404 not_found without a student name', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ status: 'not_found', credentialId: 'RS-UNKNOWN-0000' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await getPublicCertificate('RS-UNKNOWN-0000')
    expect(result).toEqual({ status: 'not_found', credentialId: 'RS-UNKNOWN-0000' })
    expect(result).not.toHaveProperty('studentName')
  })
})
