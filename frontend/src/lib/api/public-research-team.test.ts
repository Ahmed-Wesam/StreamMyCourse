/**
 * @vitest-environment jsdom
 */
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { getResearchTeamRequirements } from './public-research-team'

describe('getResearchTeamRequirements', () => {
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

  it('GETs /research-team/requirements with credentials omit and no Authorization', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          courses: [
            { id: 'c1', title: 'Research Methodology' },
            { id: 'c2', title: 'Statistics & SPSS' },
          ],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    const result = await getResearchTeamRequirements()

    expect(result.courses).toEqual([
      { id: 'c1', title: 'Research Methodology' },
      { id: 'c2', title: 'Statistics & SPSS' },
    ])
    expect(fetch).toHaveBeenCalledTimes(1)
    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? []
    expect(String(url)).toMatch(/\/research-team\/requirements$/)
    expect(init?.credentials).toBe('omit')
    const headers = new Headers(init?.headers)
    expect(headers.has('Authorization')).toBe(false)
  })

  it('returns an empty courses array when the API returns none', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ courses: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await expect(getResearchTeamRequirements()).resolves.toEqual({ courses: [] })
  })

  it('does not import Amplify or the authenticated research-team client', () => {
    const dir = dirname(fileURLToPath(import.meta.url))
    const source = readFileSync(join(dir, 'public-research-team.ts'), 'utf8')
    expect(source).not.toMatch(/aws-amplify/)
    expect(source).not.toMatch(/from ['"]\.\/research-team['"]/)
    expect(source).not.toMatch(/from ['"]\.\/client['"]/)
    expect(source).not.toMatch(/from ['"]\.\/session['"]/)
  })
})
