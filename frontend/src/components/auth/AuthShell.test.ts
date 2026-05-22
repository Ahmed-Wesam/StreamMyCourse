import { beforeEach, describe, expect, it, vi } from 'vitest'

const configureAmplify = vi.hoisted(() => vi.fn())

vi.mock('aws-amplify/auth/enable-oauth-listener', () => ({}))

vi.mock('../../lib/auth', () => ({
  configureAmplify: (...args: unknown[]) => configureAmplify(...args),
}))

vi.mock('@aws-amplify/ui-react-core', () => ({
  AuthenticatorProvider: ({ children }: { children: unknown }) => children,
}))

vi.mock('./PostLoginRedirect', () => ({
  PostLoginRedirect: () => null,
}))

vi.mock('./StudentProfileBootstrap', () => ({
  StudentProfileBootstrap: () => null,
}))

describe('AuthShell', () => {
  beforeEach(() => {
    configureAmplify.mockClear()
    vi.resetModules()
  })

  it('calls configureAmplify when the auth chunk module loads', async () => {
    await import('./AuthShell')
    expect(configureAmplify).toHaveBeenCalledTimes(1)
  })
})
