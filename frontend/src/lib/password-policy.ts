export type PasswordCheckId = 'length' | 'upper' | 'lower' | 'number'

export const PASSWORD_CHECK_LABELS: Record<PasswordCheckId, string> = {
  length: 'At least 8 characters',
  upper: 'One uppercase letter',
  lower: 'One lowercase letter',
  number: 'One number',
}

export function passwordChecks(password: string): Record<PasswordCheckId, boolean> {
  return {
    length: password.length >= 8,
    upper: /[A-Z]/.test(password),
    lower: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
  }
}

export function isPasswordPolicyMet(password: string): boolean {
  const checks = passwordChecks(password)
  return Object.values(checks).every(Boolean)
}
