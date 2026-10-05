/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const getPurchases = vi.fn()

vi.mock('../../lib/api/billing', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../../lib/api/billing')>()
  return {
    ...mod,
    getPurchases: (...args: unknown[]) => getPurchases(...args),
  }
})

import AccountPurchasesPage from './AccountPurchasesPage'

describe('AccountPurchasesPage', () => {
  beforeEach(() => {
    getPurchases.mockReset()
  })

  afterEach(() => {
    cleanup()
  })

  it('shows prototype Billing & Purchase History heading', async () => {
    getPurchases.mockResolvedValue([])

    render(
      <MemoryRouter>
        <AccountPurchasesPage />
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: /billing & purchase history/i })).toBeTruthy()
  })

  it('shows empty state when there are no purchases', async () => {
    getPurchases.mockResolvedValue([])

    render(
      <MemoryRouter>
        <AccountPurchasesPage />
      </MemoryRouter>,
    )

    expect(await screen.findByTestId('purchases-empty')).toBeTruthy()
    expect(screen.getByText(/have not purchased/i)).toBeTruthy()
  })

  it('lists paid purchases with formatted amounts', async () => {
    getPurchases.mockResolvedValue([
      {
        id: 'p1',
        productType: 'bundle',
        status: 'paid',
        amountMinor: 150_000,
        currency: 'JOD',
        createdAt: '2026-03-01T12:00:00.000Z',
      },
    ])

    render(
      <MemoryRouter>
        <AccountPurchasesPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Research Mastery Bundle')).toBeTruthy()
    })
    expect(screen.getByText(/JOD\s*150/)).toBeTruthy()
    expect(screen.getByText(/Paid/i)).toBeTruthy()
  })
})
