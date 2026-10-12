/**
 * @vitest-environment jsdom
 */
import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { HyperPayWidget } from './HyperPayWidget'

describe('HyperPayWidget', () => {
  afterEach(() => {
    cleanup()
    document.querySelectorAll('script[src*="paymentWidgets"]').forEach((el) => el.remove())
    delete (window as Window & { wpwlOptions?: unknown }).wpwlOptions
  })

  it('renders COPYandPAY form with shopper result URL and loads widget script', () => {
    render(
      <HyperPayWidget
        widgetScriptUrl="https://eu-test.oppwa.com/v1/paymentWidgets.js?checkoutId=CHK-1"
        integrity="sha384-test"
        shopperResultUrl="https://researchspectrum.org/billing/result"
      />,
    )

    const form = document.querySelector('form.paymentWidgets')
    expect(form).toBeTruthy()
    expect(form?.getAttribute('action')).toBe('https://researchspectrum.org/billing/result')
    expect(form?.getAttribute('data-brands')).toBe('VISA MASTER')

    const script = document.querySelector('script[src*="paymentWidgets"]')
    expect(script?.getAttribute('integrity')).toBe('sha384-test')
    expect(script?.getAttribute('crossorigin')).toBe('anonymous')

    expect((window as Window & { wpwlOptions?: unknown }).wpwlOptions).toBeUndefined()
  })
})
