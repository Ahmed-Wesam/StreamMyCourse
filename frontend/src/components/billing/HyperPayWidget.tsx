import { useEffect, useRef } from 'react'

type HyperPayWidgetProps = {
  widgetScriptUrl: string
  integrity: string
  shopperResultUrl: string
}

/** Embeds the HyperPay COPYandPAY widget (VISA / Mastercard). */
export function HyperPayWidget({ widgetScriptUrl, integrity, shopperResultUrl }: HyperPayWidgetProps) {
  const formRef = useRef<HTMLFormElement>(null)

  useEffect(() => {
    const script = document.createElement('script')
    script.src = widgetScriptUrl
    script.setAttribute('integrity', integrity)
    script.setAttribute('crossorigin', 'anonymous')
    script.async = true
    document.body.appendChild(script)

    return () => {
      script.remove()
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
