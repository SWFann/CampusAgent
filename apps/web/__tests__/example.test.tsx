import { render, screen } from '@testing-library/react'
import HomePage from '../src/app/page'

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter() {
    return {
      push: jest.fn(),
    }
  },
}))

describe('HomePage', () => {
  it('renders CampusAgent title', () => {
    render(<HomePage />)
    const title = screen.getByText('CampusAgent')
    expect(title).toBeInTheDocument()
  })

  it('renders description', () => {
    render(<HomePage />)
    const description = screen.getByText(/Privacy-first/i)
    expect(description).toBeInTheDocument()
  })
})
