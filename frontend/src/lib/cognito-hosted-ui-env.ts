/**
 * Pure predicate: Cognito Hosted UI OAuth is ready when pool id, client id, and Hosted UI domain
 * are all present as non-whitespace strings. Parity with `scripts/check-cognito-spa-env.mjs` once
 * pool + client are set (checker also fails the build without domain).
 */
export function cognitoHostedUiEnvComplete(
  poolId: string | undefined | null,
  clientId: string | undefined | null,
  domain: string | undefined | null,
): boolean {
  const p = String(poolId ?? '').trim()
  const c = String(clientId ?? '').trim()
  const d = String(domain ?? '').trim()
  return Boolean(p && c && d)
}
