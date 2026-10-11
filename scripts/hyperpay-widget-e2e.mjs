/**
 * Prod checkout-session → local widget page → test card → 3DS (eu-test portal txn).
 * Requires: frontend/node_modules (puppeteer-core), Chrome, .env.local passwords.
 */
import { createRequire } from 'node:module'
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import http from 'node:http'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const require = createRequire(path.join(fileURLToPath(new URL('.', import.meta.url)), '../frontend/package.json'))
const puppeteer = require('puppeteer-core')

const ROOT = path.join(fileURLToPath(new URL('.', import.meta.url)), '..')
const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const AWS = 'C:\\Program Files\\Amazon\\AWSCLIV2\\aws.exe'
const API = 'https://spjxahk3gg.execute-api.eu-west-1.amazonaws.com/prod'

function loadEnvLocal() {
  const p = path.join(ROOT, '.env.local')
  if (!fs.existsSync(p)) throw new Error('missing .env.local')
  const out = {}
  for (const line of fs.readFileSync(p, 'utf8').split(/\r?\n/)) {
    const m = line.match(/^([A-Z0-9_]+)=(.*)$/)
    if (m) out[m[1]] = m[2].trim().replace(/^["']|["']$/g, '')
  }
  return out
}

function mintStudentJwt(env) {
  const pool = execFileSync(
    AWS,
    [
      'cloudformation',
      'describe-stacks',
      '--stack-name',
      'StreamMyCourse-Auth-prod',
      '--region',
      'eu-west-1',
      '--query',
      "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue | [0]",
      '--output',
      'text',
    ],
    { encoding: 'utf8' },
  ).trim()
  const client = execFileSync(
    AWS,
    [
      'cloudformation',
      'describe-stacks',
      '--stack-name',
      'StreamMyCourse-Auth-prod',
      '--region',
      'eu-west-1',
      '--query',
      "Stacks[0].Outputs[?OutputKey=='TeacherUserPoolClientId'].OutputValue | [0]",
      '--output',
      'text',
    ],
    { encoding: 'utf8' },
  ).trim()
  const user = process.env.LOCAL_COGNITO_USERNAME_STUDENT || env.LOCAL_COGNITO_USERNAME_STUDENT || 'billing-e2e@noreply.local'
  const pass = env.LOCAL_COGNITO_PASSWORD_STUDENT
  if (!pass) throw new Error('LOCAL_COGNITO_PASSWORD_STUDENT missing')
  const auth = JSON.stringify({
    UserPoolId: pool,
    ClientId: client,
    AuthFlow: 'ADMIN_USER_PASSWORD_AUTH',
    AuthParameters: { USERNAME: user, PASSWORD: pass },
  })
  return execFileSync(
    AWS,
    [
      'cognito-idp',
      'admin-initiate-auth',
      '--cli-input-json',
      auth,
      '--region',
      'eu-west-1',
      '--query',
      'AuthenticationResult.IdToken',
      '--output',
      'text',
    ],
    { encoding: 'utf8' },
  ).trim()
}

async function createCheckoutSession(jwt) {
  const res = await fetch(`${API}/billing/checkout-session`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${jwt}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      productType: 'bundle',
      billing: {
        givenName: 'Widget',
        surname: 'E2E',
        street: '1 Test Street',
        city: 'Amman',
        state: 'Amman',
        postcode: '11118',
        country: 'JO',
      },
    }),
  })
  const text = await res.text()
  if (!res.ok) throw new Error(`checkout-session ${res.status}: ${text.slice(0, 300)}`)
  return JSON.parse(text)
}

function serveHtml(html) {
  return new Promise((resolve) => {
    const server = http.createServer((_req, res) => {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' })
      res.end(html)
    })
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port
      resolve({ server, url: `http://127.0.0.1:${port}/` })
    })
  })
}

function buildWidgetHtml(session) {
  const action = session.shopperResultUrl
  const src = session.widgetScriptUrl
  return `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>HyperPay widget e2e</title></head>
<body>
<form action="${action}" class="paymentWidgets" data-brands="VISA MASTER"></form>
<script src="${src}"></script>
</body></html>`
}

async function main() {
  if (!fs.existsSync(CHROME)) throw new Error(`Chrome not found at ${CHROME}`)
  const env = loadEnvLocal()
  const jwt = mintStudentJwt(env)
  const session = await createCheckoutSession(jwt)
  console.log('purchaseId', session.purchaseId)
  console.log('checkoutId', session.checkoutId)
  const html = buildWidgetHtml(session)
  const { server, url } = await serveHtml(html)
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: true,
    args: ['--no-first-run', '--disable-web-security'],
  })
  try {
    const page = await browser.newPage()
    page.setDefaultTimeout(120000)
    page.on('console', (msg) => console.log('browser:', msg.text()))
    page.on('pageerror', (err) => console.log('pageerror:', err.message))
    await page.goto(url, { waitUntil: 'domcontentloaded' })
    await page.waitForFunction(
      () => document.querySelector('.wpwl-control-cardNumber input') !== null,
      { timeout: 120000 },
    )
    await new Promise((r) => setTimeout(r, 1000))
    await page.screenshot({ path: path.join(ROOT, '.tmp-widget-page.png'), fullPage: true })
    await page.click('.wpwl-control-cardNumber input')
    await page.type('.wpwl-control-cardNumber input', '4012000033330026', { delay: 15 })
    await page.click('.wpwl-control-cardHolder input')
    await page.type('.wpwl-control-cardHolder input', 'Test User', { delay: 10 })
    await page.select('.wpwl-control-expiryMonth select', '01')
    await page.select('.wpwl-control-expiryYear select', '39')
    await page.click('.wpwl-control-cvv input')
    await page.type('.wpwl-control-cvv input', '100', { delay: 10 })
    await page.click('button.wpwl-button-pay')
    await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 120000 }).catch(() => {})
    // 3DS simulator: submit challenge if present
    await new Promise((r) => setTimeout(r, 2000))
    const submit =
      (await page.$('input[type="submit"]')) ||
      (await page.$('button[type="submit"]')) ||
      (await page.$('#submit'))
    if (submit) await submit.click()
    await new Promise((r) => setTimeout(r, 5000))
    console.log('final_url', page.url())
    console.log('Done — check merchant portal and GET /billing/purchases for paid')
  } finally {
    await browser.close()
    server.close()
  }
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
