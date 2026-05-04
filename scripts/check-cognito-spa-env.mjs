#!/usr/bin/env node
/**
 * Enforce SPA Cognito OAuth env contract at build time:
 * if VITE_COGNITO_USER_POOL_ID and VITE_COGNITO_USER_POOL_CLIENT_ID are both set,
 * VITE_COGNITO_DOMAIN must be set (Hosted UI host for OAuth code flow).
 *
 * Loads VITE_* keys from frontend/.env* (same layering as Vite production build)
 * so local `npm run build:*` matches CI when vars live only in .env files.
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, '..')
const frontendDir = path.join(repoRoot, 'frontend')

const VITE_FILES = [
  '.env',
  '.env.local',
  '.env.production',
  '.env.production.local',
]

function parseEnvFile(filePath) {
  const out = {}
  if (!fs.existsSync(filePath)) return out
  const text = fs.readFileSync(filePath, 'utf8')
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eq = trimmed.indexOf('=')
    if (eq === -1) continue
    const key = trimmed.slice(0, eq).trim()
    let val = trimmed.slice(eq + 1).trim()
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1)
    }
    out[key] = val
  }
  return out
}

function loadFrontendViteEnv() {
  const fromFiles = {}
  for (const name of VITE_FILES) {
    const parsed = parseEnvFile(path.join(frontendDir, name))
    Object.assign(fromFiles, parsed)
  }
  return fromFiles
}

function effective(name, fileEnv) {
  const fromProc = process.env[name]
  if (fromProc !== undefined && fromProc !== null && String(fromProc).trim() !== '') {
    return String(fromProc).trim()
  }
  return String(fileEnv[name] ?? '').trim()
}

/** When set (e.g. unit tests), do not read `frontend/.env*` so subprocess env is authoritative. */
const skipDotenv = ['1', 'true', 'yes'].includes(
  String(process.env.COGNITO_SPA_ENV_NO_DOTENV ?? '').toLowerCase(),
)
const fileEnv = skipDotenv ? {} : loadFrontendViteEnv()
const pool = effective('VITE_COGNITO_USER_POOL_ID', fileEnv)
const client = effective('VITE_COGNITO_USER_POOL_CLIENT_ID', fileEnv)
const domain = effective('VITE_COGNITO_DOMAIN', fileEnv)

if (!pool) {
  process.exit(0)
}

if (!client) {
  console.error(
    'check-cognito-spa-env: VITE_COGNITO_USER_POOL_ID is set but VITE_COGNITO_USER_POOL_CLIENT_ID is missing or empty. Set both together (or clear the pool id for a non-auth build).',
  )
  process.exit(1)
}

if (!domain) {
  console.error(
    'check-cognito-spa-env: VITE_COGNITO_USER_POOL_ID and VITE_COGNITO_USER_POOL_CLIENT_ID are set but VITE_COGNITO_DOMAIN is missing. OAuth / Hosted UI requires the Cognito domain host (e.g. prefix.auth.eu-west-1.amazoncognito.com). Set VITE_COGNITO_DOMAIN in CI env or frontend/.env.production.',
  )
  process.exit(1)
}

process.exit(0)
