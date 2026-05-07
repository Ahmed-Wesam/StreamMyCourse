/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const amplifyConfigure = vi.hoisted(() => vi.fn())

vi.mock('aws-amplify', () => ({
  Amplify: {
    configure: (...args: unknown[]) => amplifyConfigure(...args),
  },
}))

import { configureAmplify, isAuthConfigured } from './auth'

describe('isAuthConfigured', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('returns false when any Cognito env value is missing or blank', () => {
    vi.stubEnv('VITE_COGNITO_USER_POOL_ID', 'pool')
    vi.stubEnv('VITE_COGNITO_USER_POOL_CLIENT_ID', 'client')
    vi.stubEnv('VITE_COGNITO_DOMAIN', '')
    expect(isAuthConfigured()).toBe(false)

    vi.stubEnv('VITE_COGNITO_DOMAIN', 'd.example.com')
    vi.stubEnv('VITE_COGNITO_USER_POOL_ID', '   ')
    expect(isAuthConfigured()).toBe(false)
  })

  it('returns true when pool, client, and domain are non-empty after trim', () => {
    vi.stubEnv('VITE_COGNITO_USER_POOL_ID', '  eu-west-1_x  ')
    vi.stubEnv('VITE_COGNITO_USER_POOL_CLIENT_ID', 'abc')
    vi.stubEnv('VITE_COGNITO_DOMAIN', 'host.auth.region.amazoncognito.com')
    expect(isAuthConfigured()).toBe(true)
  })
})

describe('configureAmplify', () => {
  beforeEach(() => {
    amplifyConfigure.mockClear()
    vi.stubGlobal('location', { origin: 'https://learn.example.com' } as Location)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('does nothing when Cognito env is incomplete', () => {
    vi.stubEnv('VITE_COGNITO_USER_POOL_ID', '')
    vi.stubEnv('VITE_COGNITO_USER_POOL_CLIENT_ID', 'c')
    vi.stubEnv('VITE_COGNITO_DOMAIN', 'd')
    configureAmplify()
    expect(amplifyConfigure).not.toHaveBeenCalled()
  })

  it('calls Amplify.configure with OAuth when env is complete', () => {
    vi.stubEnv('VITE_COGNITO_USER_POOL_ID', 'eu-west-1_pool')
    vi.stubEnv('VITE_COGNITO_USER_POOL_CLIENT_ID', 'clientid')
    vi.stubEnv('VITE_COGNITO_DOMAIN', 'myapp.auth.eu-west-1.amazoncognito.com')
    configureAmplify()
    expect(amplifyConfigure).toHaveBeenCalledTimes(1)
    const arg = amplifyConfigure.mock.calls[0][0] as {
      Auth: {
        Cognito: {
          userPoolId: string
          userPoolClientId: string
          loginWith: { oauth: { domain: string; redirectSignIn: string[] } }
        }
      }
    }
    expect(arg.Auth.Cognito.userPoolId).toBe('eu-west-1_pool')
    expect(arg.Auth.Cognito.userPoolClientId).toBe('clientid')
    expect(arg.Auth.Cognito.loginWith.oauth.domain).toBe('myapp.auth.eu-west-1.amazoncognito.com')
    expect(arg.Auth.Cognito.loginWith.oauth.redirectSignIn).toEqual(['https://learn.example.com/'])
  })

  it.skipIf(!import.meta.env.DEV)('replaces IPv6 loopback with 127.0.0.1 in dev before Amplify', () => {
    const replace = vi.fn()
    vi.stubEnv('VITE_COGNITO_USER_POOL_ID', 'eu-west-1_pool')
    vi.stubEnv('VITE_COGNITO_USER_POOL_CLIENT_ID', 'clientid')
    vi.stubEnv('VITE_COGNITO_DOMAIN', 'myapp.auth.eu-west-1.amazoncognito.com')
    vi.stubGlobal(
      'location',
      {
        href: 'http://[::1]:5174/courses/x?a=1#h',
        hostname: '[::1]',
        protocol: 'http:',
        replace,
      } as unknown as Location,
    )
    configureAmplify()
    expect(replace).toHaveBeenCalledWith('http://127.0.0.1:5174/courses/x?a=1#h')
    expect(amplifyConfigure).not.toHaveBeenCalled()
  })

  it.skipIf(!import.meta.env.DEV)('replaces IPv6 loopback when port is implicit (default http)', () => {
    const replace = vi.fn()
    vi.stubEnv('VITE_COGNITO_USER_POOL_ID', 'eu-west-1_pool')
    vi.stubEnv('VITE_COGNITO_USER_POOL_CLIENT_ID', 'clientid')
    vi.stubEnv('VITE_COGNITO_DOMAIN', 'myapp.auth.eu-west-1.amazoncognito.com')
    vi.stubGlobal(
      'location',
      {
        href: 'http://[::1]/',
        hostname: '[::1]',
        protocol: 'http:',
        replace,
      } as unknown as Location,
    )
    configureAmplify()
    expect(replace).toHaveBeenCalledWith('http://127.0.0.1/')
    expect(amplifyConfigure).not.toHaveBeenCalled()
  })

  it.skipIf(!import.meta.env.DEV)('registers loopback OAuth redirects in dev for localhost Vite host', () => {
    vi.stubEnv('VITE_COGNITO_USER_POOL_ID', 'eu-west-1_pool')
    vi.stubEnv('VITE_COGNITO_USER_POOL_CLIENT_ID', 'clientid')
    vi.stubEnv('VITE_COGNITO_DOMAIN', 'myapp.auth.eu-west-1.amazoncognito.com')
    vi.stubGlobal(
      'location',
      {
        origin: 'http://localhost:5174',
        hostname: 'localhost',
        port: '5174',
        protocol: 'http:',
      } as Location,
    )
    configureAmplify()
    const arg = amplifyConfigure.mock.calls[0][0] as {
      Auth: { Cognito: { loginWith: { oauth: { redirectSignIn: string[] } } } }
    }
    const redirects = arg.Auth.Cognito.loginWith.oauth.redirectSignIn
    expect(redirects).toContain('http://localhost:5174/')
    expect(redirects).toContain('http://127.0.0.1:5174/')
    expect(redirects).toHaveLength(2)
  })
})
