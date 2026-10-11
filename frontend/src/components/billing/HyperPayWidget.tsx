import { useEffect, useRef } from 'react'

type HyperPayWidgetProps = {
  widgetScriptUrl: string
  integrity: string
  shopperResultUrl: string
}

declare global {
  interface Window {
    wpwlOptions?: Record<string, unknown>
  }
}

/** Embeds the HyperPay COPYandPAY widget (VISA / Mastercard). */
export function HyperPayWidget({ widgetScriptUrl, integrity, shopperResultUrl }: HyperPayWidgetProps) {
  const formRef = useRef<HTMLFormElement>(null)

  useEffect(() => {
    // Do not set paymentTarget "_top". That sent Pay straight to the result
    // page and skipped HyperPay's bank-check redirect.
    delete window.wpwlOptions

    const script = document.createElement('script')
    script.src = widgetScriptUrl
    const skipIntegrity = import.meta.env.VITE_HYPERPAY_SKIP_WIDGET_INTEGRITY === 'true'
    if (integrity && !skipIntegrity) {
      script.setAttribute('integrity', integrity)
      script.setAttribute('crossorigin', 'anonymous')
    }
    script.async = false
    document.body.appendChild(script)

    return () => {
      script.remove()
      delete window.wpwlOptions
    }
  }, [widgetScriptUrl, integrity])

  return (
    <form
      ref={formRef}
      action={shopperResultUrl}
      className="paymentWidgets"
      data-brands="VISA MASTER"
      data-testid="hyperpay-widget-form"
    />
  )
}
