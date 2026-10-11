/**
 * Complete HyperPay test 3DS for a pending S2S payment (eu-test portal success).
 */
import { execFileSync } from 'node:child_process'
import { createRequire } from 'node:module'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const require = createRequire(path.join(fileURLToPath(new URL('.', import.meta.url)), '../frontend/package.json'))
const puppeteer = require('puppeteer-core')
const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const ROOT = path.join(fileURLToPath(new URL('.', import.meta.url)), '..')

function redirectUrl() {
  let out = ''
  try {
    out = execFileSync('python', [path.join(ROOT, 'scripts', 'hyperpay_eu_test_s2s_smoke.py')], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    })
  } catch (err) {
    out = `${err.stdout || ''}${err.stderr || ''}`
  }
  const line = out.split(/\r?\n/).find((l) => l.startsWith('REDIRECT_URL='))
  if (!line) throw new Error('no REDIRECT_URL in smoke output')
  return line.slice('REDIRECT_URL='.length).trim()
}

async function main() {
  const url = redirectUrl()
  console.log('opening', url.slice(0, 100), '...')
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: true })
  const page = await browser.newPage()
  page.setDefaultTimeout(120000)
  await page.goto(url, { waitUntil: 'domcontentloaded' })
  await new Promise((r) => setTimeout(r, 2000))
  const submitted = await page.evaluate(() => {
    const form = document.querySelector('form')
    if (form) {
      form.submit()
      return 'form'
    }
    const btn = document.querySelector('input[type=submit], button[type=submit], #submit')
    if (btn) {
      btn.click()
      return 'button'
    }
    return ''
  })
  console.log('submit via', submitted || 'none')
  await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 120000 }).catch(() => {})
  await new Promise((r) => setTimeout(r, 3000))
  console.log('final', page.url().slice(0, 160))
  await browser.close()
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
