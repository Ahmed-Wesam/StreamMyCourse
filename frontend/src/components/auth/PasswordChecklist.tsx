import { Check, Circle } from 'lucide-react'

import {
  PASSWORD_CHECK_LABELS,
  passwordChecks,
  type PasswordCheckId,
} from '../../lib/password-policy'

const ORDER: PasswordCheckId[] = ['length', 'upper', 'lower', 'number']

type PasswordChecklistProps = {
  password: string
}

export function PasswordChecklist({ password }: PasswordChecklistProps) {
  const checks = passwordChecks(password)
  return (
    <ul className="mt-2 space-y-1.5" data-testid="password-checklist">
      {ORDER.map((id) => {
        const met = checks[id]
        return (
          <li key={id} className="flex items-center gap-2 text-[13px] font-semibold text-rs-body">
            {met ? (
              <Check aria-hidden className="size-3.5 text-emerald-600" strokeWidth={2.5} />
            ) : (
              <Circle aria-hidden className="size-3.5 text-rs-muted" strokeWidth={2} />
            )}
            <span className={met ? 'text-rs-navy' : undefined}>{PASSWORD_CHECK_LABELS[id]}</span>
          </li>
        )
      })}
    </ul>
  )
}
