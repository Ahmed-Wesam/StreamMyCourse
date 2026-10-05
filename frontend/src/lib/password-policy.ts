export type PasswordCheckId = 'length' | 'upper' | 'lower' | 'number'

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
