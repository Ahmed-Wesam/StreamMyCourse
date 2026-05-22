import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const fetchMe = vi.hoisted(() => vi.fn())
const hasSignedInIdToken = vi.hoisted(() => vi.fn())
const isAuthConfigured = vi.hoisted(() => vi.fn())
const configureAmplify = vi.hoisted(() => vi.fn())

vi.mock('./auth', () => ({
  isAuthConfigured: () => isAuthConfigured(),
  configureAmplify: (...args: unknown[]) => configureAmplify(...args),
}))

vi.mock('./api/session', () => ({
  hasSignedInIdToken: () => hasSignedInIdToken(),
  fetchMe: () => fetchMe(),
}))

describe('auth-session-lazy', () => {
  beforeEach(async () => {
    vi.resetModules()
    fetchMe.mockReset()
    hasSignedInIdToken.mockReset()
    isAuthConfigured.mockReset()
    configureAmplify.mockReset()
    isAuthConfigured.mockReturnValue(true)
    const mod = await import('./auth-session-lazy')
    mod.resetProfileWarmState()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('probeSignedIn calls configureAmplify before hasSignedInIdToken', async () => {
    hasSignedInIdToken.mockResolvedValue(true)
    const { probeSignedIn } = await import('./auth-session-lazy')
    await probeSignedIn()
    expect(configureAmplify).toHaveBeenCalledTimes(1)
    expect(hasSignedInIdToken).toHaveBeenCalledTimes(1)
  })

  it('warmUserProfileOnce calls fetchMe once when already signed in', async () => {
    fetchMe.mockResolvedValue({ id: 'u1', email: 'a@b.c' })

    const { warmUserProfileOnce, resetProfileWarmState } = await import('./auth-session-lazy')
    await warmUserProfileOnce(true)
    await warmUserProfileOnce(true)

    expect(fetchMe).toHaveBeenCalledTimes(1)
    expect(hasSignedInIdToken).not.toHaveBeenCalled()
    resetProfileWarmState()
  })

  it('warmUserProfileOnce skips fetchMe when markUserProfileWarmed was called', async () => {
    fetchMe.mockResolvedValue({ id: 'u1', email: 'a@b.c' })

    const { markUserProfileWarmed, warmUserProfileOnce } = await import('./auth-session-lazy')
    markUserProfileWarmed()
    await warmUserProfileOnce(true)

    expect(fetchMe).not.toHaveBeenCalled()
  })

  it('warmUserProfileOnce probes session when alreadySignedIn is false', async () => {
    hasSignedInIdToken.mockResolvedValue(true)
    fetchMe.mockResolvedValue({ id: 'u1', email: 'a@b.c' })

    const { warmUserProfileOnce } = await import('./auth-session-lazy')
    await warmUserProfileOnce()

    expect(hasSignedInIdToken).toHaveBeenCalledTimes(1)
    expect(fetchMe).toHaveBeenCalledTimes(1)
  })

  it('resetProfileWarmState allows a second warm after sign-out path', async () => {
    fetchMe.mockResolvedValue({ id: 'u1', email: 'a@b.c' })

    const { warmUserProfileOnce, resetProfileWarmState } = await import('./auth-session-lazy')
    await warmUserProfileOnce(true)
    resetProfileWarmState()
    await warmUserProfileOnce(true)

    expect(fetchMe).toHaveBeenCalledTimes(2)
  })
})
