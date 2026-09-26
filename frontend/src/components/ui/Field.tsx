import {
  Children,
  cloneElement,
  isValidElement,
  useId,
  type InputHTMLAttributes,
  type ReactElement,
  type ReactNode,
} from 'react'

type FieldProps = {
  label: string
  hint?: string
  error?: string
  children?: ReactNode
} & Omit<InputHTMLAttributes<HTMLInputElement>, 'children' | 'id'>

export function Field({ label, hint, error, children, className, ...inputProps }: FieldProps) {
  const reactId = useId()
  const inputId = `field-${reactId}`
  const hintId = hint ? `${inputId}-hint` : undefined
  const errorId = error ? `${inputId}-error` : undefined
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined

  const controlClass = [
    'w-full px-[14px] py-[11px] border-[1.5px] border-solid border-rs-line rounded-xl font-inherit text-[15px] text-rs-ink bg-white outline-none transition duration-200 ease-rs leading-normal',
    'focus:border-rs-blue focus:shadow-[0_0_0_3px_rgba(30,94,255,.10)]',
    'placeholder:text-rs-muted',
    error
      ? 'border-red-500 shadow-[0_0_0_3px_rgba(239,68,68,.08)] focus:border-red-500 focus:shadow-[0_0_0_3px_rgba(239,68,68,.12)]'
      : null,
    className,
  ]
    .filter(Boolean)
    .join(' ')

  let control: ReactNode
  if (children != null) {
    const child = Children.only(children)
    if (!isValidElement(child)) {
      throw new Error('Field expects a single React element child')
    }
    const el = child as ReactElement<Record<string, unknown>>
    const existingDescribedBy =
      typeof el.props['aria-describedby'] === 'string' ? el.props['aria-describedby'] : undefined
    const mergedDescribedBy = [existingDescribedBy, describedBy].filter(Boolean).join(' ') || undefined
    control = cloneElement(el, {
      id: inputId,
      'aria-invalid': error ? true : el.props['aria-invalid'],
      'aria-describedby': mergedDescribedBy,
      className: [controlClass, el.props.className].filter(Boolean).join(' '),
    })
  } else {
    control = (
      <input
        {...inputProps}
        id={inputId}
        className={controlClass}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
      />
    )
  }

  return (
    <div className={error ? 'mb-4 has-err' : 'mb-4'}>
      <label
        htmlFor={inputId}
        className="block text-[13px] font-bold text-rs-navy mb-1.5 tracking-[-0.005em]"
      >
        {label}
      </label>
      {control}
      {hint ? (
        <p id={hintId} className="mt-1.5 text-[12.5px] font-semibold text-rs-muted leading-snug">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="mt-[5px] text-[12.5px] font-semibold text-[#b91c1c] leading-snug">
          {error}
        </p>
      ) : null}
    </div>
  )
}
