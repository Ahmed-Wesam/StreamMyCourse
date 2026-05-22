import { describe, expect, it, vi } from 'vitest'

const useAuthenticatorFromCore = vi.hoisted(() =>
  vi.fn(() => ({ authStatus: 'from-ui-react-core' })),
)
const useAuthenticatorFromUiReact = vi.hoisted(() =>
  vi.fn(() => ({ authStatus: 'from-ui-react' })),
)

vi.mock('@aws-amplify/ui-react-core', () => ({
  useAuthenticator: useAuthenticatorFromCore,
}))

vi.mock('@aws-amplify/ui-react', () => ({
  useAuthenticator: useAuthenticatorFromUiReact,
}))

describe('auth-ui', () => {
  it('re-exports useAuthenticator from @aws-amplify/ui-react-core (not @aws-amplify/ui-react)', async () => {
    const { useAuthenticator } = await import('./auth-ui')

    expect(
      useAuthenticator,
      'useAuthenticator must be re-exported from @aws-amplify/ui-react-core, not @aws-amplify/ui-react',
    ).toBe(useAuthenticatorFromCore)
    expect(useAuthenticator).not.toBe(useAuthenticatorFromUiReact)
  })
})
