import { ArrowRight } from 'lucide-react'
import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from 'react'
import { Link, type LinkProps } from 'react-router-dom'

type Variant = 'primary' | 'ghost' | 'onDark' | 'ghostOnDark'
type Size = 'md' | 'sm'

type CommonProps = {
  variant?: Variant
  size?: Size
  arrow?: boolean
  disabled?: boolean
  className?: string
  children?: ReactNode
}

type ButtonAsButton = CommonProps &
  Omit<ButtonHTMLAttributes<HTMLButtonElement>, keyof CommonProps | 'href'> & {
    to?: undefined
    href?: undefined
  }

type ButtonAsLink = CommonProps &
  Omit<LinkProps, keyof CommonProps | 'to'> & {
    to: string
    href?: undefined
  }

type ButtonAsAnchor = CommonProps &
  Omit<AnchorHTMLAttributes<HTMLAnchorElement>, keyof CommonProps | 'href'> & {
    href: string
    to?: undefined
  }

type ButtonProps = ButtonAsButton | ButtonAsLink | ButtonAsAnchor

const VARIANT_CLASS: Record<Variant, string> = {
  primary: 'rs-btn-primary',
  ghost: 'rs-btn-ghost',
  onDark: 'rs-btn-on-dark',
  ghostOnDark: 'rs-btn-ghost-on-dark',
}

function cx(...parts: Array<string | undefined | false>) {
  return parts.filter(Boolean).join(' ')
}

function ButtonContent({
  children,
  arrow,
}: {
  children: ReactNode
  arrow?: boolean
}) {
  return (
    <>
      {children}
      {arrow ? (
        <ArrowRight aria-hidden size={17} className="rs-btn-arrow rs-btn-arrow-slide" />
      ) : null}
    </>
  )
}

export function Button(props: ButtonProps) {
  const {
    variant = 'primary',
    size = 'md',
    arrow = false,
    disabled = false,
    className,
    children,
    ...rest
  } = props

  const classes = cx('group', 'rs-btn', VARIANT_CLASS[variant], size === 'sm' && 'rs-btn-sm', className)

  if ('to' in props && props.to != null) {
    const { to, onClick, ...linkRest } = rest as Omit<ButtonAsLink, keyof CommonProps>
    return (
      <Link
        {...linkRest}
        to={disabled ? '#' : to}
        className={classes}
        aria-disabled={disabled ? true : undefined}
        tabIndex={disabled ? -1 : linkRest.tabIndex}
        onClick={(event) => {
          if (disabled) {
            event.preventDefault()
            return
          }
          onClick?.(event)
        }}
      >
        <ButtonContent arrow={arrow}>{children}</ButtonContent>
      </Link>
    )
  }

  if ('href' in props && props.href != null) {
    const { href, onClick, ...anchorRest } = rest as Omit<ButtonAsAnchor, keyof CommonProps>
    return (
      <a
        {...anchorRest}
        href={disabled ? undefined : href}
        className={classes}
        aria-disabled={disabled ? true : undefined}
        tabIndex={disabled ? -1 : anchorRest.tabIndex}
        onClick={(event) => {
          if (disabled) {
            event.preventDefault()
            return
          }
          onClick?.(event)
        }}
      >
        <ButtonContent arrow={arrow}>{children}</ButtonContent>
      </a>
    )
  }

  const { type = 'button', ...buttonRest } = rest as Omit<ButtonAsButton, keyof CommonProps>
  return (
    <button {...buttonRest} type={type} disabled={disabled} className={classes}>
      <ButtonContent arrow={arrow}>{children}</ButtonContent>
    </button>
  )
}
