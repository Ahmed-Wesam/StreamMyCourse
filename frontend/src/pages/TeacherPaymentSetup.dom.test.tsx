/**
 * @vitest-environment jsdom
 */
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import TeacherPaymentSetup from './TeacherPaymentSetup'

describe('TeacherPaymentSetup', () => {
  it('says pricing is closed', async () => {
    render(
      <MemoryRouter initialEntries={['/settings/payments']}>
        <Routes>
          <Route path="/settings/payments" element={<TeacherPaymentSetup />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(await screen.findByRole('heading', { name: /Pricing is closed/i })).toBeTruthy()
  })
})
