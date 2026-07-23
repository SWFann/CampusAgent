/**
 * Homepage tests.
 * The new homepage is a workbench that requires authentication.
 */

import { render, screen, waitFor } from '@testing-library/react'
import HomePage from '../src/app/page'

// Mock next/navigation
jest.mock('next/navigation', () => ({
  usePathname: () => '/',
  useRouter() {
    return {
      push: jest.fn(),
    }
  },
}))

// Mock fetch
global.fetch = jest.fn() as jest.MockedFunction<typeof fetch>

function mockAuthenticated() {
  (global.fetch as jest.Mock).mockImplementation((url: string) => {
    if (url.includes('/auth/me')) {
      return Promise.resolve({
        status: 200,
        json: async () => ({
          success: true,
          data: { id: '1', email: 'test@test.com', display_name: '测试用户', global_role: 'USER' },
        }),
      })
    }
    // Return empty data for all other endpoints
    return Promise.resolve({
      status: 200,
      json: async () => ({ success: true, data: [] }),
    })
  })
}

describe('HomePage', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    Object.defineProperty(document, 'cookie', {
      value: 'csrf_token=test-token',
      writable: true,
    })
  })

  it('renders the personalized today heading for an authenticated user', async () => {
    mockAuthenticated()
    render(<HomePage />)
    await waitFor(() => {
      expect(screen.getByText('你好！测试用户')).toBeInTheDocument()
    })
  })

  it('shows the complete platform capability overview', async () => {
    mockAuthenticated()
    render(<HomePage />)
    // Wait for auth to load and page to render
    await waitFor(() => {
      expect(screen.getAllByText('个人工作台').length).toBeGreaterThan(0)
      expect(screen.getByText('重要信息，不再淹没')).toBeInTheDocument()
      expect(screen.getByText('少跑一步，进度清楚')).toBeInTheDocument()
      expect(screen.getByText('让不同声音形成共识')).toBeInTheDocument()
    })
  })
})
