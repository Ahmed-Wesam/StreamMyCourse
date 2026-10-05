/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const amplifyConfigure = vi.hoisted(() => vi.fn())
const setKeyValueStorage = vi.hoisted(() => vi.fn())

vi.mock('aws-amplify', () => ({
  Amplify: {
    configure: (...args: unknown[]) => amplifyConfigure(...args),
  },
}))

vi.mock('aws-amplify/auth/cognito', () => ({
  cognitoUserPoolsTokenProvider: {
    setKeyValueStorage: (...args: unknown[]) => setKeyValueStorage(...args),
  },
}))

import { CookieStorage, defaultStorage } from 'aws-amplify/utils'

import { applyRememberMeStorage, configureAmplify, isAuthConfigured, keepDefaultAuthStorage } from './auth'
import { AUTH_REMEMBER_ME_FLAG, clearAmplifyAuthCaches } from './clear-amplify-auth-caches'

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
    setKeyValueStorage.mockReset()
    localStorage.clear()
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
          loginWith: { email: boolean; oauth: { domain: string; redirectSignIn: string[] } }
        }
      }
    }
    expect(arg.Auth.Cognito.userPoolId).toBe('eu-west-1_pool')
    expect(arg.Auth.Cognito.userPoolClientId).toBe('clientid')
    expect(arg.Auth.Cognito.loginWith.email).toBe(true)
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

  it('applies session CookieStorage before Amplify.configure when remember-me is off', () => {
    localStorage.setItem(AUTH_REMEMBER_ME_FLAG, 'session')
    vi.stubEnv('VITE_COGNITO_USER_POOL_ID', 'eu-west-1_pool')
    vi.stubEnv('VITE_COGNITO_USER_POOL_CLIENT_ID', 'clientid')
    vi.stubEnv('VITE_COGNITO_DOMAIN', 'myapp.auth.eu-west-1.amazoncognito.com')
    const order: string[] = []
    setKeyValueStorage.mockImplementation(() => {
      order.push('storage')
    })
    amplifyConfigure.mockImplementation(() => {
      order.push('configure')
    })

    configureAmplify()

    expect(order).toEqual(['storage', 'configure'])
    const storage = setKeyValueStorage.mock.calls[0][0] as CookieStorage
    expect(storage).toBeInstanceOf(CookieStorage)
    expect(storage.secure).toBe(true)
    expect(storage.sameSite).toBe('lax')
    expect(storage.expires).toBeUndefined()
  })
})

describe('remember me storage', () => {
  beforeEach(() => {
    setKeyValueStorage.mockReset()
    localStorage.clear()
  })

  it('unchecked selects CookieStorage with no expires', () => {
    applyRememberMeStorage(false)

    expect(setKeyValueStorage).toHaveBeenCalledTimes(1)
    const storage = setKeyValueStorage.mock.calls[0][0] as CookieStorage
    expect(storage).toBeInstanceOf(CookieStorage)
    expect(storage.secure).toBe(true)
    expect(storage.sameSite).toBe('lax')
    expect(storage.expires).toBeUndefined()
    expect(localStorage.getItem(AUTH_REMEMBER_ME_FLAG)).toBe('session')
  })

  it('checked uses default storage', () => {
    applyRememberMeStorage(true)

    expect(setKeyValueStorage).toHaveBeenCalledTimes(1)
    expect(setKeyValueStorage).toHaveBeenCalledWith(defaultStorage)
    expect(localStorage.getItem(AUTH_REMEMBER_ME_FLAG)).toBe('remember')
  })

  it('Google redirect keeps default storage and clears a session-only flag', () => {
    localStorage.setItem(AUTH_REMEMBER_ME_FLAG, 'session')

    keepDefaultAuthStorage()

    expect(setKeyValueStorage).toHaveBeenCalledWith(defaultStorage)
    expect(localStorage.getItem(AUTH_REMEMBER_ME_FLAG)).toBeNull()
  })

  it('clears the non-secret remember-me flag with Amplify auth caches', () => {
    localStorage.setItem(AUTH_REMEMBER_ME_FLAG, 'session')

    clearAmplifyAuthCaches()

    expect(localStorage.getItem(AUTH_REMEMBER_ME_FLAG)).toBeNull()
  })
})
