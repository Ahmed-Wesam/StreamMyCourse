import { useEffect, useRef } from 'react'

type HyperPayWidgetProps = {
  widgetScriptUrl: string
  integrity: string
  shopperResultUrl: string
}

declare global {
  interface Window {
    wpwlOptions?: { paymentTarget: string }
  }
}

/** Embeds the HyperPay COPYandPAY widget (VISA / Mastercard). */
export function HyperPayWidget({ widgetScriptUrl, integrity, shopperResultUrl }: HyperPayWidgetProps) {
  const formRef = useRef<HTMLFormElement>(null)

  useEffect(() => {
    window.wpwlOptions = { paymentTarget: '_top' }

    const script = document.createElement('script')
    script.src = widgetScriptUrl
    script.setAttribute('integrity', integrity)
    script.setAttribute('crossorigin', 'anonymous')
    script.async = true
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
