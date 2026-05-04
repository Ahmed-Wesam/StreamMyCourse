/**
 * @vitest-environment jsdom
 */
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchAuthSessionMock = vi.hoisted(() => vi.fn())

vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: (...args: unknown[]) => fetchAuthSessionMock(...args),
}))

import {
  displayNameFromAttributes,
  loadMergedProfileAttributes,
  useCognitoDisplayName,
} from './cognito-display-name'

describe('displayNameFromAttributes', () => {
  it('prefers given_name', () => {
    expect(
      displayNameFromAttributes(
        { given_name: '  Sam  ', email: 'sam@example.com' },
        'Google_103690698188818697243',
      ),
    ).toBe('Sam')
  })

  it('uses first word of name when given_name missing', () => {
    expect(
      displayNameFromAttributes({ name: 'Pat Example', email: 'pat@example.com' }, 'Google_1'),
    ).toBe('Pat')
  })

  it('uses email local part for opaque username when no name fields', () => {
    expect(displayNameFromAttributes({ email: 'jane.doe@gmail.com' }, 'Google_103690698188818697243')).toBe(
      'jane.doe',
    )
  })

  it('uses email local part when username is email-shaped', () => {
    expect(
      displayNameFromAttributes({ email: 'teacher@example.com' }, 'teacher@example.com'),
    ).toBe('teacher')
  })
})

describe('loadMergedProfileAttributes', () => {
  beforeEach(() => {
    fetchAuthSessionMock.mockReset()
  })

  it('falls back to id token claims when pool attrs are empty', async () => {
    fetchAuthSessionMock.mockResolvedValue({
      tokens: { idToken: { payload: { email: 'jane@gmail.com', name: 'Jane Doe' } } },
    })

    const attrs = await loadMergedProfileAttributes()
    expect(displayNameFromAttributes(attrs, 'Google_103690698188818697243')).toBe('Jane')
  })

  it('lets pool attrs override token claims when provided', async () => {
    fetchAuthSessionMock.mockResolvedValue({
      tokens: { idToken: { payload: { email: 'from-token@gmail.com' } } },
    })

    const attrs = await loadMergedProfileAttributes({ email: 'from-api@gmail.com' })
    expect(attrs.email).toBe('from-api@gmail.com')
  })

  it('keeps id token given_name when pool supplies empty given_name', async () => {
    fetchAuthSessionMock.mockResolvedValue({
      tokens: { idToken: { payload: { given_name: 'Jamie', email: 'jamie@example.com' } } },
    })

    const attrs = await loadMergedProfileAttributes({ given_name: '', email: 'jamie@example.com' })
    expect(displayNameFromAttributes(attrs, 'Google_1')).toBe('Jamie')
  })

  it('uses id token email only when pool is empty and name fields are absent', async () => {
    fetchAuthSessionMock.mockResolvedValue({
      tokens: { idToken: { payload: { email: 'jane.doe@gmail.com' } } },
    })

    const attrs = await loadMergedProfileAttributes()
    expect(displayNameFromAttributes(attrs, 'Google_1')).toBe('jane.doe')
  })
})

describe('useCognitoDisplayName', () => {
  beforeEach(() => {
    fetchAuthSessionMock.mockReset()
  })

  it('stays not ready with empty label until profile attributes resolve', async () => {
    fetchAuthSessionMock.mockResolvedValue({
      tokens: { idToken: { payload: { given_name: 'Casey' } } },
    })

    const { result } = renderHook(() => useCognitoDisplayName('Google_1'))
    expect(result.current.ready).toBe(false)
    expect(result.current.label).toBe('')

    await waitFor(() => {
      expect(result.current.ready).toBe(true)
    })
    expect(result.current.label).toBe('Casey')
  })

  it('is ready with empty label when there is no username', () => {
    const { result } = renderHook(() => useCognitoDisplayName(undefined))
    expect(result.current.ready).toBe(true)
    expect(result.current.label).toBe('')
  })
})
