/**
 * P12-11: Frontend security tests.
 *
 * Verifies:
 * - Storage audit detects sensitive keys.
 * - isSensitiveValue flags tokens/passwords.
 * - clearSensitiveKey removes sensitive entries.
 * - Empty storage reports no leaks.
 */

import { auditStorage, clearSensitiveKey, isSensitiveValue } from '@/lib/security/storage-audit'

beforeEach(() => {
  window.localStorage.clear()
  window.sessionStorage.clear()
})

describe('storage audit', () => {
  it('reports no leaks on empty storage', () => {
    const result = auditStorage()
    expect(result.hasLeaks).toBe(false)
    expect(result.leaks).toHaveLength(0)
  })

  it('detects access_token in localStorage', () => {
    window.localStorage.setItem('access_token', 'eyJfake')
    const result = auditStorage()
    expect(result.hasLeaks).toBe(true)
    expect(result.leaks[0].storage).toBe('localStorage')
    expect(result.leaks[0].key).toBe('access_token')
  })

  it('detects password in sessionStorage', () => {
    window.sessionStorage.setItem('password', 'secret')
    const result = auditStorage()
    expect(result.hasLeaks).toBe(true)
    expect(result.leaks[0].storage).toBe('sessionStorage')
  })

  it('detects private_preference key', () => {
    window.localStorage.setItem('private_preference', 'data')
    const result = auditStorage()
    expect(result.hasLeaks).toBe(true)
  })

  it('does not flag non-sensitive keys', () => {
    window.localStorage.setItem('theme', 'dark')
    window.localStorage.setItem('locale', 'zh-CN')
    const result = auditStorage()
    expect(result.hasLeaks).toBe(false)
  })
})

describe('isSensitiveValue', () => {
  it('flags token-like values', () => {
    expect(isSensitiveValue('access_token')).toBe(true)
    expect(isSensitiveValue('refresh_token')).toBe(true)
    expect(isSensitiveValue('password')).toBe(true)
    expect(isSensitiveValue('api_key')).toBe(true)
  })

  it('does not flag safe values', () => {
    expect(isSensitiveValue('theme')).toBe(false)
    expect(isSensitiveValue('locale')).toBe(false)
  })
})

describe('clearSensitiveKey', () => {
  it('removes a sensitive key from localStorage', () => {
    window.localStorage.setItem('access_token', 'eyJfake')
    const removed = clearSensitiveKey('localStorage', 'access_token')
    expect(removed).toBe(true)
    expect(window.localStorage.getItem('access_token')).toBeNull()
  })

  it('does not remove non-sensitive keys', () => {
    window.localStorage.setItem('theme', 'dark')
    const removed = clearSensitiveKey('localStorage', 'theme')
    expect(removed).toBe(false)
    expect(window.localStorage.getItem('theme')).toBe('dark')
  })
})
