/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import ResearchTeamPage from './ResearchTeamPage'

function renderResearchTeam() {
  return render(
    <MemoryRouter>
      <ResearchTeamPage />
    </MemoryRouter>,
  )
}

describe('ResearchTeamPage', () => {
  afterEach(() => {
    cleanup()
  })

  it('shows eligibility copy, courses and eligibility links, and no Apply control', () => {
    renderResearchTeam()

    expect(
      screen.getByText(
        /Eligibility does not guarantee acceptance\. Selection considers interviews/i,
      ),
    ).toBeTruthy()

    expect(screen.queryByRole('button', { name: /apply|submit application/i })).toBeNull()
    expect(screen.queryByRole('link', { name: /apply|submit application/i })).toBeNull()

    const coursesLinks = screen
      .getAllByRole('link')
      .filter((link) => (link.getAttribute('href') ?? '') === '/courses')
    expect(coursesLinks.length).toBeGreaterThan(0)

    const eligibilityLinks = screen
      .getAllByRole('link')
      .filter((link) => (link.getAttribute('href') ?? '') === '#eligibility')
    expect(eligibilityLinks.length).toBeGreaterThan(0)
  })
})
