#!/usr/bin/env node
/**
 * Side-by-side screenshots of Bahaa's prototype HTML and the local student preview.
 *
 * Usage (from frontend/):
 *   npm run compare:prototype -- home
 *   npm run compare:prototype -- all
 *
 * puppeteer-core is a frontend devDependency. This file lives at the repo root
 * and loads it from frontend/node_modules. Chrome is the installed browser;
 * nothing is downloaded.
 */
import { spawn, execFile } from 'node:child_process'
import { createRequire } from 'node:module'
import fs from 'node:fs'
import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { promisify } from 'node:util'
import {
  resolveCompareDeepLinkRouteInBrowser,
  resolveComparePageRoute,
  resolveStudentCognitoViteEnv,
} from './compare-prototype-resolve.mjs'

const execFileAsync = promisify(execFile)

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, '..')
const frontendDir = path.join(repoRoot, 'frontend')
const outDir = path.join(frontendDir, '.prototype-compare')

const require = createRequire(path.join(frontendDir, 'package.json'))
const puppeteer = require('puppeteer-core')

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const PROTOTYPE_DIR = 'D:\\Desktop\\Website\\Frontend Course'
const PROTOTYPE_URL_DIR = 'file:///D:/Desktop/Website/Frontend%20Course'
const LOCAL_ORIGIN = 'http://localhost:5173'
const PREVIEW_PROBE = 'http://127.0.0.1:5173/'
const STUDENT_EMAIL = 'ci-student@noreply.local'
const API_STACK = 'StreamMyCourse-Api-prod'

const VIEWPORTS = [
  { name: '1440', width: 1440, height: 900 },
  { name: '390', width: 390, height: 844 },
]

/**
 * Visible state for scroll-reveal blocks. Homepage.html and
 * frontend/src/styles/prototype-base.css use `.reveal.in`.
 * The extra transition rule keeps the full-page shot off the 0.7s fade.
 */
const REVEAL_CSS = '.reveal.in{opacity:1!important;transform:none!important;transition:none!important}'

/**
 * Demo chrome is injected by each prototype page, not by nav.js or data.js.
 * Homepage.html (and the other pages) create #rs-dev-widget / .rs-dev-toggle ("Demo State").
 * Login.html has .demo-card ("Demo Student Account").
 */
const HIDE_DEMO_CSS = '#rs-dev-widget{display:none!important}.demo-card{display:none!important}'

/**
 * Every RS-16 inventory page. `compare: false` pages have no prototype file.
 * /verify-email has no prototype page; ForgotPassword.html is the layout reference.
 * Checkout opens the bundle order (`productType=bundle`) so the screen is the
 * checkout form rather than the invalid-link state. The inventory route is /checkout.
 * Lesson, quiz, and assignment resolve via authenticated catalog GETs on Research Methodology.
 * verify-credential uses the RS-16 seed certificate id from scripts/rs16-seed/courses.json.
 */
const PAGES = [
  { name: 'home', label: 'Home', prototypeFile: 'Homepage.html', route: '/', auth: false, compare: true },
  { name: 'courses', label: 'Courses', prototypeFile: 'Courses.html', route: '/courses', auth: false, compare: true },
  { name: 'course-methodology', label: 'Course: Research Methodology', prototypeFile: 'Methodology.html', route: '/courses/:courseId', auth: false, compare: true, resolve: 'course', courseKey: 'methodology' },
  { name: 'course-statistics', label: 'Course: Statistics & SPSS', prototypeFile: 'Statistics.html', route: '/courses/:courseId', auth: false, compare: true, resolve: 'course', courseKey: 'statistics' },
  { name: 'course-writing', label: 'Course: Scientific Writing', prototypeFile: 'Writing.html', route: '/courses/:courseId', auth: false, compare: true, resolve: 'course', courseKey: 'writing' },
  { name: 'course-sr-ma', label: 'Course: Systematic Reviews & Meta-Analysis', prototypeFile: 'SR_MA.html', route: '/courses/:courseId', auth: false, compare: true, resolve: 'course', courseKey: 'srma' },
  { name: 'about', label: 'About', prototypeFile: 'AboutInstructor.html', route: '/about', auth: false, compare: true },
  { name: 'faq', label: 'FAQ', prototypeFile: 'FAQ.html', route: '/faq', auth: false, compare: true },
  { name: 'research-team', label: 'Research Team', prototypeFile: 'ResearchTeam.html', route: '/research-team', auth: false, compare: true },
  { name: 'contact', label: 'Contact', prototypeFile: 'Contact.html', route: '/contact', auth: false, compare: true },
  { name: 'verify', label: 'Verify', prototypeFile: 'CertificateVerification.html', route: '/verify', auth: false, compare: true },
  { name: 'verify-credential', label: 'Verify credential', prototypeFile: 'CertificateVerification.html', route: '/verify/:credentialId', auth: false, compare: true, resolve: 'credential' },
  { name: 'login', label: 'Login', prototypeFile: 'Login.html', route: '/login', auth: false, compare: true },
  { name: 'register', label: 'Register', prototypeFile: 'Register.html', route: '/register', auth: false, compare: true },
  { name: 'forgot-password', label: 'Forgot password', prototypeFile: 'ForgotPassword.html', route: '/forgot-password', auth: false, compare: true },
  { name: 'reset-password', label: 'Reset password', prototypeFile: 'ResetPassword.html', route: '/reset-password', auth: false, compare: true },
  { name: 'verify-email', label: 'Verify email', prototypeFile: 'ForgotPassword.html', route: '/verify-email', auth: false, compare: true },
  { name: 'privacy', label: 'Privacy', prototypeFile: 'PrivacyPolicy.html', route: '/privacy', auth: false, compare: true },
  { name: 'terms', label: 'Terms', prototypeFile: 'TermsOfService.html', route: '/terms', auth: false, compare: true },
  { name: 'refund', label: 'Refund', prototypeFile: 'RefundPolicy.html', route: '/refund', auth: false, compare: true },
  { name: 'delivery', label: 'Delivery', prototypeFile: 'DeliveryPolicy.html', route: '/delivery', auth: false, compare: true },
  { name: 'educational-disclaimer', label: 'Educational disclaimer', prototypeFile: 'EducationalDisclaimer.html', route: '/educational-disclaimer', auth: false, compare: true },
  { name: 'billing-success', label: 'Billing success', prototypeFile: null, route: '/billing/success', auth: false, compare: false },
  { name: 'billing-cancel', label: 'Billing cancel', prototypeFile: null, route: '/billing/cancel', auth: false, compare: false },
  { name: 'research-team-apply', label: 'Apply Research Team', prototypeFile: 'ApplyResearchTeam.html', route: '/research-team/apply', auth: true, compare: true },
  { name: 'certificates', label: 'Certificates', prototypeFile: 'Certificates.html', route: '/certificates', auth: true, compare: true },
  { name: 'dashboard', label: 'Dashboard', prototypeFile: 'Dashboard.html', route: '/dashboard', auth: true, compare: true },
  { name: 'account-profile', label: 'Account profile', prototypeFile: 'Account.html', route: '/account/profile', auth: true, compare: true },
  { name: 'account-purchases', label: 'Account purchases', prototypeFile: 'Account.html', route: '/account/purchases', auth: true, compare: true },
  { name: 'settings', label: 'Settings', prototypeFile: 'Settings.html', route: '/settings', auth: true, compare: true },
  { name: 'checkout', label: 'Checkout', prototypeFile: 'Checkout.html', route: '/checkout?productType=bundle', auth: true, compare: true },
  { name: 'lesson', label: 'Lesson', prototypeFile: 'MediaPlayer.html', route: '/courses/:courseId/lessons/:lessonId', auth: true, compare: true, resolve: 'lesson', courseKey: 'methodology' },
  { name: 'quiz', label: 'Quiz', prototypeFile: 'Quiz.html', route: '/courses/:courseId/modules/:moduleId/quiz', auth: true, compare: true, resolve: 'quiz', courseKey: 'methodology' },
  { name: 'assignment', label: 'Assignment', prototypeFile: 'Assignment.html', route: '/courses/:courseId/assignments/:assignmentId', auth: true, compare: true, resolve: 'assignment', courseKey: 'methodology' },
]

function usage() {
  const names = PAGES.map((page) => page.name).join(', ')
  return `Usage: npm run compare:prototype -- <page>|all\nPages: ${names}`
}

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
    if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
      val = val.slice(1, -1)
    }
    out[key] = val
  }
  return out
}

function readLocalCognitoPassword() {
  const file = parseEnvFile(path.join(repoRoot, '.env.local'))
  const student =
    typeof file.LOCAL_COGNITO_PASSWORD_STUDENT === 'string' ? file.LOCAL_COGNITO_PASSWORD_STUDENT.trim() : ''
  return student
}

function redact(text, secret) {
  if (!secret || !text) return text
  return String(text).split(secret).join('[redacted]')
}

function viteProductionApiBaseFromFiles() {
  const names = ['.env', '.env.local', '.env.production', '.env.production.local']
  const merged = {}
  for (const name of names) {
    Object.assign(merged, parseEnvFile(path.join(frontendDir, name)))
  }
  const fromProc = (process.env.VITE_API_BASE_URL || '').trim()
  const value = (fromProc || merged.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '')
  if (value.startsWith('https://')) return value
  return ''
}

function awsExecutable() {
  if (process.platform === 'win32') {
    const candidate = path.join(process.env.ProgramFiles || 'C:\\Program Files', 'Amazon', 'AWSCLIV2', 'aws.exe')
    if (fs.existsSync(candidate)) return candidate
  }
  return 'aws'
}

async function prodApiEndpointFromStack() {
  const region = process.env.AWS_REGION || process.env.AWS_DEFAULT_REGION || 'eu-west-1'
  const { stdout } = await execFileAsync(
    awsExecutable(),
    [
      'cloudformation',
      'describe-stacks',
      '--stack-name',
      API_STACK,
      '--region',
      region,
      '--query',
      "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue | [0]",
      '--output',
      'text',
      '--no-cli-pager',
    ],
    { windowsHide: true },
  )
  const url = stdout.trim().replace(/\/+$/, '')
  if (!url.startsWith('https://') || url === 'None') {
    throw new Error(`Could not resolve ApiEndpoint from ${API_STACK} in ${region}.`)
  }
  return url
}

async function resolveProdApiBase() {
  const fromEnv = viteProductionApiBaseFromFiles()
  if (fromEnv) return fromEnv
  const endpoint = await prodApiEndpointFromStack()
  const host = new URL(endpoint).host
  const stage = new URL(endpoint).pathname
  console.log(
    `frontend Vite env has no absolute VITE_API_BASE_URL (local dev uses /api plus the proxy). Preview has no proxy, so the student build uses ${API_STACK} ApiEndpoint (${host}${stage}).`,
  )
  return endpoint
}

function studentIndexHtml() {
  return path.join(frontendDir, 'dist', 'student', 'index.html')
}

function studentDistLooksLikeTeacher() {
  const indexPath = studentIndexHtml()
  if (!fs.existsSync(indexPath)) return false
  const html = fs.readFileSync(indexPath, 'utf8')
  return /teacher-[\w-]+\.js/.test(html) && !/student-[\w-]+\.js/.test(html)
}

function distStudentAssetsText() {
  const assets = path.join(frontendDir, 'dist', 'student', 'assets')
  if (!fs.existsSync(assets)) return ''
  let text = ''
  for (const name of fs.readdirSync(assets)) {
    if (!name.endsWith('.js')) continue
    text += fs.readFileSync(path.join(assets, name), 'utf8')
  }
  return text
}

function distBakesApiBase(apiBase) {
  const needle = apiBase.replace(/\/+$/, '')
  return distStudentAssetsText().includes(needle)
}

function distBakesCognitoEnv(cognitoEnv) {
  const client = cognitoEnv.VITE_COGNITO_USER_POOL_CLIENT_ID
  const pool = cognitoEnv.VITE_COGNITO_USER_POOL_ID
  if (!client || !pool) return false
  const text = distStudentAssetsText()
  return text.includes(client) && text.includes(pool)
}

function runCommand(commandLine, options) {
  return new Promise((resolve, reject) => {
    const child = spawn(commandLine, {
      cwd: frontendDir,
      shell: true,
      stdio: 'inherit',
      windowsHide: true,
      ...options,
    })
    child.on('error', reject)
    child.on('exit', (code) => {
      if (code === 0) resolve()
      else reject(new Error(`${commandLine} exited ${code}`))
    })
  })
}

async function ensureStudentBuild(apiBase, cognitoEnv) {
  const indexPath = studentIndexHtml()
  const missing = !fs.existsSync(indexPath)
  const teacherOnly = studentDistLooksLikeTeacher()
  const staleApi = !missing && !teacherOnly && !distBakesApiBase(apiBase)
  const staleCognito = !missing && !teacherOnly && !distBakesCognitoEnv(cognitoEnv)
  if (!missing && !teacherOnly && !staleApi && !staleCognito) {
    console.log('Using existing frontend/dist/student (prod API + student Cognito).')
    return
  }
  if (teacherOnly) {
    console.log('frontend/dist/student looks like a teacher build. Rebuilding the student app.')
  } else if (missing) {
    console.log('frontend/dist/student is missing. Building the student app.')
  } else if (staleApi) {
    console.log('frontend/dist/student does not call the prod API. Rebuilding the student app.')
  } else {
    console.log('frontend/dist/student does not bake prod student Cognito. Rebuilding the student app.')
  }
  await runCommand('npm run build', {
    env: {
      ...process.env,
      VITE_API_BASE_URL: apiBase,
      VITE_COGNITO_USER_POOL_ID: cognitoEnv.VITE_COGNITO_USER_POOL_ID,
      VITE_COGNITO_USER_POOL_CLIENT_ID: cognitoEnv.VITE_COGNITO_USER_POOL_CLIENT_ID,
      VITE_COGNITO_DOMAIN: cognitoEnv.VITE_COGNITO_DOMAIN,
    },
  })
  if (!distBakesApiBase(apiBase)) {
    throw new Error('Student build finished but the prod API URL is not in frontend/dist/student.')
  }
  if (!distBakesCognitoEnv(cognitoEnv)) {
    throw new Error('Student build finished but prod Cognito ids are not in frontend/dist/student.')
  }
}

function startPreview() {
  const child = spawn(
    'npx --no-install vite preview --config vite.student.config.ts --port 5173 --strictPort --host 127.0.0.1',
    {
      cwd: frontendDir,
      shell: true,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    },
  )
  let log = ''
  const append = (chunk) => {
    log += chunk.toString()
    if (log.length > 12000) log = log.slice(-12000)
  }
  child.stdout.on('data', append)
  child.stderr.on('data', append)
  child.previewLog = () => log
  return child
}

async function waitForPreview(child) {
  const deadline = Date.now() + 30000
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(`vite preview exited ${child.exitCode}.\n${child.previewLog()}`)
    }
    try {
      const res = await fetch(PREVIEW_PROBE)
      if (res.ok) return
    } catch {
      /* preview still starting */
    }
    await new Promise((resolve) => setTimeout(resolve, 300))
  }
  throw new Error(`vite preview did not answer ${PREVIEW_PROBE}.\n${child.previewLog()}`)
}

function killProcessTree(child) {
  return new Promise((resolve) => {
    if (!child || child.pid == null) {
      resolve()
      return
    }
    if (process.platform === 'win32') {
      execFile('taskkill', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true }, () => resolve())
      return
    }
    child.kill('SIGTERM')
    resolve()
  })
}

async function removeDir(dir) {
  if (!dir) return
  for (let attempt = 0; attempt < 5; attempt += 1) {
    try {
      await rm(dir, { recursive: true, force: true })
      return
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 400))
    }
  }
}

function prototypeUrl(fileName) {
  return `${PROTOTYPE_URL_DIR}/${encodeURIComponent(fileName)}`
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

async function resolveLocalRoute(browserPage, page, apiBase, password) {
  const needsBrowserSession =
    page.resolve === 'lesson' || page.resolve === 'quiz' || page.resolve === 'assignment'
  if (needsBrowserSession) {
    return resolveCompareDeepLinkRouteInBrowser(browserPage, page, apiBase, repoRoot)
  }
  return resolveComparePageRoute(page, apiBase, {
    repoRoot,
    studentPassword: password,
    mintStudentIdToken: async () => {
      throw new Error('mintStudentIdToken is only used for lesson/quiz/assignment via browser session.')
    },
  })
}

async function preparePage(page, { prototype }) {
  await page.evaluate(async () => {
    if (document.fonts && document.fonts.ready) await document.fonts.ready
    document.querySelectorAll('.reveal').forEach((el) => el.classList.add('in'))
  })
  const css = prototype ? `${REVEAL_CSS}\n${HIDE_DEMO_CSS}` : REVEAL_CSS
  await page.addStyleTag({ content: css })
}

async function seedPrototypeDashboardAuth(browserPage) {
  if (browserPage.__prototypeDashboardAuthSeeded) return
  await browserPage.evaluateOnNewDocument(() => {
    if (!location.href.includes('Dashboard.html')) return
    const key = 'rs_platform_state_v1'
    let current = {}
    try {
      current = JSON.parse(localStorage.getItem(key) || '{}')
    } catch {
      current = {}
    }
    if (current.authed) return
    localStorage.setItem(
      key,
      JSON.stringify({
        authed: true,
        name: current.name || 'Student',
        ownedCourses: Array.isArray(current.ownedCourses) ? current.ownedCourses : [],
        courseProgress: current.courseProgress || {
          'research-methodology': 0,
          'statistics-spss': 0,
          'scientific-writing': 0,
          'systematic-reviews-meta-analysis': 0,
        },
        completedCourses: Array.isArray(current.completedCourses) ? current.completedCourses : [],
        certificates: Array.isArray(current.certificates) ? current.certificates : [],
      }),
    )
  })
  browserPage.__prototypeDashboardAuthSeeded = true
}

async function openAndShot(browserPage, url, filePath, { prototype, readySelector, readyHeading }) {
  await browserPage.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 })
  if (readyHeading || readySelector) {
    try {
      if (readyHeading) {
        await browserPage.waitForFunction(
          (text) => {
            const heading = document.querySelector('h1')
            return Boolean(heading && (heading.textContent || '').includes(text))
          },
          { timeout: 25000 },
          readyHeading,
        )
      } else {
        await browserPage.waitForSelector(readySelector, { timeout: 25000 })
      }
    } catch (err) {
      const snapshot = await browserPage.evaluate(() => ({
        path: location.pathname,
        title: document.title,
        h1: (document.querySelector('h1') && document.querySelector('h1').textContent) || '',
        login: Boolean(document.querySelector('input[type="password"]')),
        testIds: Array.from(document.querySelectorAll('[data-testid]'))
          .map((el) => el.getAttribute('data-testid'))
          .slice(0, 12),
      }))
      const detail = `${snapshot.path} title=${snapshot.title} h1=${snapshot.h1} loginForm=${snapshot.login} testIds=${snapshot.testIds.join(',')}`
      throw new Error(`${err instanceof Error ? err.message : String(err)} (${detail})`)
    }
  }
  try {
    await browserPage.waitForNetworkIdle({ idleTime: 500, timeout: 15000 })
  } catch {
    /* A long-lived connection should not fail the shot. */
  }
  await preparePage(browserPage, { prototype })
  await browserPage.screenshot({ path: filePath, fullPage: true, type: 'png' })
}

let signedIn = false
let signInError = null
let studentTermsReady = false

/**
 * Research Team apply redirects to /account/profile when country/profession are missing on the profile.
 * Accept terms once so dashboard (and other gated routes) can load during compare.
 */
async function ensureStudentTermsAccepted(browserPage) {
  if (studentTermsReady) return
  await browserPage.goto(`${LOCAL_ORIGIN}/dashboard`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  try {
    await browserPage.waitForFunction(
      () => {
        if (document.querySelector('[data-testid="student-page-dashboard"]')) return true
        if (location.pathname !== '/account/profile') return false
        if ((document.body.textContent || '').includes('Loading profile')) return false
        return Boolean(document.querySelector('#account-profile-heading'))
      },
      { timeout: 45000 },
    )
  } catch {
    throw new Error('Timed out waiting for dashboard or account profile after sign-in.')
  }
  const onDashboard = await browserPage.evaluate(() =>
    Boolean(document.querySelector('[data-testid="student-page-dashboard"]')),
  )
  if (onDashboard) {
    studentTermsReady = true
    return
  }
  const pathname = await browserPage.evaluate(() => location.pathname)
  if (pathname !== '/account/profile') {
    throw new Error(`Expected /dashboard or /account/profile after sign-in, got ${pathname}.`)
  }
  const boxes = await browserPage.$$('form input[type="checkbox"]')
  for (const box of boxes) {
    const checked = await box.evaluate((el) => el.checked)
    if (!checked) await box.click()
  }
  await browserPage.evaluate(() => {
    const selects = Array.from(document.querySelectorAll('form select'))
    for (const select of selects) {
      if (select.value) continue
      const option = select.options[1]
      if (option) {
        select.value = option.value
        select.dispatchEvent(new Event('change', { bubbles: true }))
      }
    }
  })
  if (boxes.length > 0) {
    const saveButton = await browserPage.waitForSelector('form button[type="submit"]', { timeout: 20000 })
    await saveButton.click()
    try {
      await browserPage.waitForFunction(
        () =>
          Boolean(document.body.textContent && document.body.textContent.includes('Profile saved.')) ||
          Boolean(document.querySelector('[data-testid="student-page-dashboard"]')),
        { timeout: 45000 },
      )
    } catch (err) {
      const detail = await browserPage.evaluate(() => {
        const alert = document.querySelector('[role="alert"]')
        return (alert && alert.textContent && alert.textContent.trim()) || ''
      })
      throw new Error(
        `${err instanceof Error ? err.message : String(err)}${detail ? ` (${detail})` : ''}`,
      )
    }
  }
  await browserPage.goto(`${LOCAL_ORIGIN}/dashboard`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  try {
    await browserPage.waitForSelector('[data-testid="student-page-dashboard"]', { timeout: 30000 })
  } catch (err) {
    const detail = await browserPage.evaluate(() => ({
      path: location.pathname,
      h1: (document.querySelector('h1') && document.querySelector('h1').textContent) || '',
    }))
    throw new Error(
      `${err instanceof Error ? err.message : String(err)} (${detail.path} h1=${detail.h1})`,
    )
  }
  studentTermsReady = true
}

async function ensureSignedIn(browserPage, password) {
  if (signedIn) return
  if (signInError) throw signInError
  if (!password) {
    signInError = new Error(
      'LOCAL_COGNITO_PASSWORD_STUDENT is missing from the repo-root .env.local. Auth pages sign in as the student user. Public pages still run.',
    )
    throw signInError
  }
  try {
    await browserPage.goto(`${LOCAL_ORIGIN}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 })
    await browserPage.waitForSelector('input[type="email"]', { timeout: 20000 })
    const remember = await browserPage.$('#rememberMe')
    if (remember) {
      const checked = await browserPage.$eval('#rememberMe', (el) => el.checked)
      if (!checked) await remember.click()
    }
    await browserPage.click('input[type="email"]', { clickCount: 3 })
    await browserPage.type('input[type="email"]', STUDENT_EMAIL, { delay: 0 })
    await browserPage.click('input[type="password"]', { clickCount: 3 })
    await browserPage.type('input[type="password"]', password, { delay: 0 })
    await browserPage.click('button[type="submit"]')
    await browserPage.waitForFunction(
      () => {
        if (location.pathname !== '/login') return true
        const alert = document.querySelector('[role="alert"]')
        return Boolean(alert && alert.textContent && alert.textContent.trim())
      },
      { timeout: 45000 },
    )
    const status = await browserPage.evaluate(() => {
      if (location.pathname !== '/login') return 'ok'
      const alert = document.querySelector('[role="alert"]')
      return (alert && alert.textContent && alert.textContent.trim()) || 'Sign-in stayed on /login.'
    })
    if (status !== 'ok') {
      throw new Error(`Sign-in as ${STUDENT_EMAIL} failed: ${redact(status, password)}`)
    }
    signedIn = true
    console.log(`Signed in as ${STUDENT_EMAIL}.`)
  } catch (err) {
    const message = redact(err instanceof Error ? err.message : String(err), password)
    signInError = new Error(message)
    throw signInError
  }
}

async function compareOne(browserPage, page, apiBase, password) {
  if (!page.compare) {
    console.log(`skip ${page.name}: no prototype file`)
    return { page, skipped: true, shots: {} }
  }
  const prototypePath = path.join(PROTOTYPE_DIR, page.prototypeFile)
  if (!fs.existsSync(prototypePath)) {
    throw new Error(`Prototype file is missing: ${prototypePath}`)
  }
  if (page.name === 'dashboard') await seedPrototypeDashboardAuth(browserPage)
  if (page.auth) await ensureSignedIn(browserPage, password)
  if (page.name === 'dashboard' || page.name === 'settings') await ensureStudentTermsAccepted(browserPage)
  const localRoute = await resolveLocalRoute(browserPage, page, apiBase, password)
  const pageDir = path.join(outDir, page.name)
  await mkdir(pageDir, { recursive: true })
  const shots = {}
  for (const viewport of VIEWPORTS) {
    await browserPage.setViewport({
      width: viewport.width,
      height: viewport.height,
      deviceScaleFactor: 1,
    })
    const prototypeName = `prototype-${viewport.name}.png`
    const localName = `local-${viewport.name}.png`
    const prototypeShot = () =>
      openAndShot(browserPage, prototypeUrl(page.prototypeFile), path.join(pageDir, prototypeName), {
        prototype: true,
        readyHeading: page.name === 'dashboard' ? 'Student Dashboard' : '',
      })
    const localShot = () =>
      openAndShot(browserPage, `${LOCAL_ORIGIN}${localRoute}`, path.join(pageDir, localName), {
        prototype: false,
        readySelector:
          page.name === 'dashboard'
            ? '[data-testid="student-page-dashboard"]'
            : page.name === 'settings'
              ? '.pg-settings'
              : '',
      })
    // Dashboard tokens are easiest to keep if the signed-in shot happens before the file:// hop.
    if (page.name === 'dashboard') {
      await localShot()
      await prototypeShot()
    } else {
      await prototypeShot()
      await localShot()
    }
    shots[`prototype-${viewport.name}`] = `${page.name}/${prototypeName}`
    shots[`local-${viewport.name}`] = `${page.name}/${localName}`
  }
  console.log(`compared ${page.name}`)
  return { page, skipped: false, shots, localRoute }
}

function renderIndex(results) {
  const sections = results.map((result) => {
    const heading = `${escapeHtml(result.page.label)} <code>${escapeHtml(result.page.route)}</code>`
    if (result.skipped) {
      return `<section><h2>${heading}</h2><p>No prototype file. Not compared.</p></section>`
    }
    if (result.error) {
      return `<section><h2>${heading}</h2><p class="error">${escapeHtml(result.error)}</p></section>`
    }
    const pairs = VIEWPORTS.map((viewport) => {
      const proto = result.shots[`prototype-${viewport.name}`]
      const local = result.shots[`local-${viewport.name}`]
      return `<h3>${viewport.width}×${viewport.height}</h3>
<div class="pair">
  <figure><figcaption>Prototype</figcaption><img src="${escapeHtml(proto)}" alt="Prototype ${viewport.name}"></figure>
  <figure><figcaption>Local</figcaption><img src="${escapeHtml(local)}" alt="Local ${viewport.name}"></figure>
</div>`
    }).join('\n')
    const resolved = result.localRoute && result.localRoute !== result.page.route
      ? `<p>Local route: <code>${escapeHtml(result.localRoute)}</code></p>`
      : ''
    return `<section><h2>${heading}</h2>${resolved}${pairs}</section>`
  })
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Prototype comparison</title>
  <style>
    body{font-family:system-ui,sans-serif;margin:24px;color:#0d1c40}
    section{margin:0 0 40px}
    .pair{display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:start}
    img{width:100%;height:auto;border:1px solid #d5def2;background:#fff}
    figcaption{font-weight:700;margin:0 0 8px}
    .error{color:#991b1b;font-weight:650}
    code{font-size:0.95em}
  </style>
</head>
<body>
  <h1>Prototype comparison</h1>
  ${sections.join('\n')}
</body>
</html>
`
}

const PAGE_ALIASES = {
  'apply-research-team': 'research-team-apply',
}

function selectPages(arg) {
  if (arg === 'all') return PAGES
  const resolved = PAGE_ALIASES[arg] ?? arg
  const page = PAGES.find((item) => item.name === resolved)
  if (!page) {
    throw new Error(`Unknown page "${arg}".\n${usage()}`)
  }
  return [page]
}

async function main() {
  const arg = process.argv[2]
  if (!arg || arg === '--help' || arg === '-h') {
    console.log(usage())
    process.exit(arg ? 0 : 1)
  }
  if (!fs.existsSync(CHROME_PATH)) {
    throw new Error(`Chrome was not found at ${CHROME_PATH}`)
  }
  const selected = selectPages(arg)
  const ordered = [
    ...selected.filter((page) => !page.auth),
    ...selected.filter((page) => page.auth),
  ]
  const apiBase = await resolveProdApiBase()
  const cognitoEnv = await resolveStudentCognitoViteEnv({
    frontendDir,
    execFileAsync,
    awsExecutable: awsExecutable(),
    preferAuthStack: true,
  })
  await ensureStudentBuild(apiBase, cognitoEnv)
  const password = readLocalCognitoPassword()
  const preview = startPreview()
  let browser = null
  let userDataDir = null
  const results = []
  try {
    await waitForPreview(preview)
    userDataDir = await mkdtemp(path.join(os.tmpdir(), 'prototype-compare-'))
    browser = await puppeteer.launch({
      executablePath: CHROME_PATH,
      headless: true,
      userDataDir,
      args: ['--no-first-run', '--no-default-browser-check', '--allow-file-access-from-files'],
    })
    const browserPage = await browser.newPage()
    browserPage.setDefaultTimeout(60000)
    await mkdir(outDir, { recursive: true })
    for (const page of ordered) {
      try {
        results.push(await compareOne(browserPage, page, apiBase, password))
      } catch (err) {
        const message = redact(err instanceof Error ? err.message : String(err), password)
        console.error(`failed ${page.name}: ${message}`)
        results.push({ page, error: message, shots: {} })
      }
    }
    await writeFile(path.join(outDir, 'index.html'), renderIndex(results), 'utf8')
  } finally {
    if (browser) await browser.close().catch(() => {})
    await killProcessTree(preview)
    await removeDir(userDataDir)
  }
  const failed = results.filter((result) => result.error)
  console.log(`Wrote ${path.join(outDir, 'index.html')}`)
  console.log(`Compared ${results.length} page(s), ${failed.length} failed.`)
  if (failed.length > 0) process.exit(1)
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : err)
  process.exit(1)
})
