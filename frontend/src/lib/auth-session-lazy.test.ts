import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const fetchMe = vi.hoisted(() => vi.fn())
const hasSignedInIdToken = vi.hoisted(() => vi.fn())
const isAuthConfigured = vi.hoisted(() => vi.fn())
const configureAmplify = vi.hoisted(() => vi.fn())
const loadMergedProfileAttributes = vi.hoisted(() => vi.fn())
const displayNameFromAttributes = vi.hoisted(() => vi.fn())

vi.mock('./auth', () => ({
  isAuthConfigured: () => isAuthConfigured(),
  configureAmplify: (...args: unknown[]) => configureAmplify(...args),
}))

vi.mock('./api/session', () => ({
  hasSignedInIdToken: () => hasSignedInIdToken(),
  fetchMe: () => fetchMe(),
}))

vi.mock('./cognito-display-name', () => ({
  loadMergedProfileAttributes: (...args: unknown[]) => loadMergedProfileAttributes(...args),
  displayNameFromAttributes: (...args: unknown[]) => displayNameFromAttributes(...args),
}))

describe('auth-session-lazy', () => {
  beforeEach(async () => {
    vi.resetModules()
    fetchMe.mockReset()
    hasSignedInIdToken.mockReset()
    isAuthConfigured.mockReset()
    configureAmplify.mockReset()
    loadMergedProfileAttributes.mockReset()
    displayNameFromAttributes.mockReset()
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

  it('probeSignedIn skips token read while student session is superseded', async () => {
    const { enterSupersededState, resetStudentSessionSupersededForTests } = await import(
      './student-session-superseded'
    )
    enterSupersededState()
    const { probeSignedIn } = await import('./auth-session-lazy')
    await expect(probeSignedIn()).resolves.toBe(false)
    expect(hasSignedInIdToken).not.toHaveBeenCalled()
    resetStudentSessionSupersededForTests()
  })

  it('probeSignedIn bypassSupersedeCheck probes while supersede handling is active', async () => {
    const { enterSupersededState, resetStudentSessionSupersededForTests } = await import(
      './student-session-superseded'
    )
    hasSignedInIdToken.mockResolvedValue(true)
    enterSupersededState()
    const { probeSignedIn } = await import('./auth-session-lazy')
    await expect(probeSignedIn({ bypassSupersedeCheck: true })).resolves.toBe(true)
    expect(hasSignedInIdToken).toHaveBeenCalledTimes(1)
    resetStudentSessionSupersededForTests()
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

  it('getProfileDisplayNameOnce caches display name and clears on resetProfileWarmState', async () => {
    fetchMe.mockResolvedValue({
      userId: 'u1',
      email: 'ada@example.com',
      role: 'student',
      cognitoSub: 'sub',
      createdAt: '',
      updatedAt: '',
    })
    loadMergedProfileAttributes.mockResolvedValue({ email: 'ada@example.com', given_name: 'Ada' })
    displayNameFromAttributes.mockReturnValue('Ada')

    const { getProfileDisplayNameOnce, resetProfileWarmState } = await import('./auth-session-lazy')
    await expect(getProfileDisplayNameOnce()).resolves.toBe('Ada')
    await expect(getProfileDisplayNameOnce()).resolves.toBe('Ada')
    expect(fetchMe).toHaveBeenCalledTimes(1)
    expect(displayNameFromAttributes).toHaveBeenCalledTimes(1)

    resetProfileWarmState()
    displayNameFromAttributes.mockReturnValue('Bob')
    fetchMe.mockResolvedValue({
      userId: 'u2',
      email: 'bob@example.com',
      role: 'student',
      cognitoSub: 'sub2',
      createdAt: '',
      updatedAt: '',
    })
    loadMergedProfileAttributes.mockResolvedValue({ email: 'bob@example.com', given_name: 'Bob' })

    await expect(getProfileDisplayNameOnce()).resolves.toBe('Bob')
    expect(fetchMe).toHaveBeenCalledTimes(2)
  })

  it('does not keep a display name that resolves after sign-out reset', async () => {
    let resolveFetch: (value: {
      userId: string
      email: string
      role: string
      cognitoSub: string
      createdAt: string
      updatedAt: string
    }) => void = () => {}
    let markFetchStarted: () => void = () => {}
    const fetchStarted = new Promise<void>((resolve) => {
      markFetchStarted = resolve
    })
    fetchMe.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveFetch = resolve
          markFetchStarted()
        }),
    )
    loadMergedProfileAttributes.mockResolvedValue({ email: 'ada@example.com', given_name: 'Ada' })
    displayNameFromAttributes.mockReturnValue('Ada')

    const { getProfileDisplayNameOnce, resetProfileWarmState } = await import('./auth-session-lazy')
    const inFlight = getProfileDisplayNameOnce()
    await fetchStarted
    resetProfileWarmState()
    resolveFetch({
      userId: 'u1',
      email: 'ada@example.com',
      role: 'student',
      cognitoSub: 'sub',
      createdAt: '',
      updatedAt: '',
    })
    await inFlight

    displayNameFromAttributes.mockReturnValue('Bob')
    fetchMe.mockResolvedValue({
      userId: 'u2',
      email: 'bob@example.com',
      role: 'student',
      cognitoSub: 'sub2',
      createdAt: '',
      updatedAt: '',
    })
    loadMergedProfileAttributes.mockResolvedValue({ email: 'bob@example.com', given_name: 'Bob' })

    await expect(getProfileDisplayNameOnce()).resolves.toBe('Bob')
  })

  it('retries a display name after a failed lookup', async () => {
    fetchMe.mockRejectedValueOnce(new Error('network'))
    loadMergedProfileAttributes.mockRejectedValueOnce(new Error('network'))

    const { getProfileDisplayNameOnce } = await import('./auth-session-lazy')
    await expect(getProfileDisplayNameOnce()).resolves.toBeNull()

    fetchMe.mockResolvedValue({
      userId: 'u1',
      email: 'ada@example.com',
      role: 'student',
      cognitoSub: 'sub',
      createdAt: '',
      updatedAt: '',
    })
    loadMergedProfileAttributes.mockResolvedValue({ email: 'ada@example.com', given_name: 'Ada' })
    displayNameFromAttributes.mockReturnValue('Ada')

    await expect(getProfileDisplayNameOnce()).resolves.toBe('Ada')
    expect(fetchMe).toHaveBeenCalledTimes(2)
  })
})
