/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { Field } from './Field'

describe('Field', () => {
  afterEach(() => {
    cleanup()
  })

  it("label's htmlFor matches the input's id", () => {
    render(
      <Field label="Email Address">
        <input type="email" />
      </Field>,
    )

    const input = screen.getByLabelText('Email Address')
    const label = screen.getByText('Email Address')
    expect(label.tagName).toBe('LABEL')
    expect(label.getAttribute('for')).toBe(input.getAttribute('id'))
    expect(input.getAttribute('id')).toBeTruthy()
  })

  it('sets aria-invalid and aria-describedby when error is set', () => {
    render(
      <Field label="Password" error="Password is required">
        <input type="password" />
      </Field>,
    )

    const input = screen.getByLabelText('Password')
    expect(input.getAttribute('aria-invalid')).toBe('true')

    const describedBy = input.getAttribute('aria-describedby')
    expect(describedBy).toBeTruthy()
    const errorEl = document.getElementById(describedBy!.split(/\s+/)[0]!)
    // describedby may include only error, or error among ids — find the error text node
    const error = screen.getByText('Password is required')
    expect(error.getAttribute('id')).toBeTruthy()
    expect(describedBy!.split(/\s+/)).toContain(error.getAttribute('id'))
    expect(errorEl || error).toBeTruthy()
  })

  it('includes hint in accessibility description when hint is set', () => {
    render(
      <Field label="Full Name" hint="As it appears on your certificate">
        <input type="text" />
      </Field>,
    )

    const input = screen.getByLabelText('Full Name')
    const hint = screen.getByText('As it appears on your certificate')
    const hintId = hint.getAttribute('id')
    expect(hintId).toBeTruthy()

    const describedBy = input.getAttribute('aria-describedby')
    expect(describedBy).toBeTruthy()
    expect(describedBy!.split(/\s+/)).toContain(hintId)
  })
})
