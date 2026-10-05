/**
 * Route resolution for scripts/compare-prototype.mjs (RS-16 deep links).
 * Pure helpers are covered by scripts/compare-prototype-resolve.test.mjs.
 */
import fs from 'node:fs'
import path from 'node:path'

/** Titles copied from Courses.html. GET /courses must contain all four. */
export const PROTOTYPE_COURSES = [
  { key: 'methodology', title: 'Research Methodology' },
  { key: 'statistics', title: 'Statistics & SPSS' },
  { key: 'writing', title: 'Scientific Writing' },
  { key: 'srma', title: 'Systematic Reviews & Meta-Analysis' },
]

export const DEFAULT_STUDENT_EMAIL = 'ci-student@noreply.local'
export const DEFAULT_AUTH_STACK = 'StreamMyCourse-Auth-prod'
export const RS16_SEED_REL = path.join('scripts', 'rs16-seed', 'courses.json')

let courseListPromise = null

export function courseIdOf(course) {
  const id = course && (course.id || course.courseId)
  return typeof id === 'string' ? id.trim() : ''
}

export function matchPrototypeCourses(courses) {
  const found = {}
  const titles = []
  for (const course of courses) {
    const title = typeof course.title === 'string' ? course.title.trim() : ''
    if (title) titles.push(title)
    const id = courseIdOf(course)
    if (!title || !id) continue
    const spec = PROTOTYPE_COURSES.find((item) => item.title.toLowerCase() === title.toLowerCase())
    if (spec && !found[spec.key]) found[spec.key] = { id, title }
  }
  const missing = PROTOTYPE_COURSES.filter((item) => !found[item.key]).map((item) => item.title)
  if (missing.length > 0) {
    const listed = titles.length > 0 ? titles.join(', ') : '(none)'
    throw new Error(
      `The four prototype courses are not seeded yet. GET /courses is missing: ${missing.join(', ')}. Titles returned: ${listed}.`,
    )
  }
  return found
}

export async function loadCourses(apiBase, fetchImpl = fetch) {
  if (!courseListPromise) {
    const url = `${apiBase.replace(/\/+$/, '')}/courses`
    courseListPromise = fetchImpl(url).then(async (res) => {
      if (!res.ok) {
        throw new Error(`GET ${url} failed with status ${res.status}.`)
      }
      const body = await res.json()
      if (!Array.isArray(body)) {
        throw new Error(`GET ${url} did not return a course array.`)
      }
      return { url, courses: body }
    })
  }
  try {
    return await courseListPromise
  } catch (err) {
    courseListPromise = null
    throw err
  }
}

/** Reset cached GET /courses (tests only). */
export function resetCourseListCacheForTests() {
  courseListPromise = null
}

export function readRs16SeedDocument(repoRoot) {
  const filePath = path.join(repoRoot, RS16_SEED_REL)
  if (!fs.existsSync(filePath)) {
    throw new Error(`RS-16 seed file is missing: ${filePath}`)
  }
  return JSON.parse(fs.readFileSync(filePath, 'utf8'))
}

function courseByTitle(doc, title) {
  const courses = Array.isArray(doc.courses) ? doc.courses : []
  const match = courses.find((c) => typeof c.title === 'string' && c.title.trim() === title.trim())
  if (!match) {
    throw new Error(`RS-16 seed courses.json has no course titled "${title}".`)
  }
  return match
}

/**
 * Public credential id RS-{certificateCode}-{UTC year}-{suffix} (matches build_seed_sql.seed_credential_id).
 */
export function credentialIdFromSeedDocument(doc, { year } = {}) {
  const cert = doc.certificate
  if (!cert || typeof cert.courseTitle !== 'string') {
    throw new Error('RS-16 seed certificate config is missing courseTitle.')
  }
  const course = courseByTitle(doc, cert.courseTitle)
  const code = String(course.certificateCode || '').trim()
  const suffix = String(cert.suffix || '').trim()
  if (!/^[0-9A-Fa-f]{6}$/.test(code)) {
    throw new Error('RS-16 seed certificateCode must be 6 hex characters.')
  }
  if (!/^[0-9A-Fa-f]{10}$/.test(suffix)) {
    throw new Error('RS-16 seed certificate suffix must be 10 hex characters.')
  }
  const utcYear = year ?? new Date().getUTCFullYear()
  if (!Number.isInteger(utcYear)) {
    throw new Error('year must be an integer.')
  }
  return `RS-${code.toUpperCase()}-${utcYear}-${suffix.toUpperCase()}`
}

export function buildVerifyRoute(credentialId) {
  return `/verify/${encodeURIComponent(credentialId)}`
}

export function buildLessonRoute(courseId, lessonId) {
  return `/courses/${encodeURIComponent(courseId)}/lessons/${encodeURIComponent(lessonId)}`
}

export function buildQuizRoute(courseId, moduleId) {
  return `/courses/${encodeURIComponent(courseId)}/modules/${encodeURIComponent(moduleId)}/quiz`
}

export function buildAssignmentRoute(courseId, assignmentId) {
  return `/courses/${encodeURIComponent(courseId)}/assignments/${encodeURIComponent(assignmentId)}`
}

function lessonSortKey(lesson) {
  const moduleOrder = Number.isFinite(lesson.moduleOrder) ? lesson.moduleOrder : 0
  const order = Number.isFinite(lesson.order) ? lesson.order : 0
  return moduleOrder * 10000 + order
}

export function pickFirstLessonId(lessons) {
  if (!Array.isArray(lessons) || lessons.length === 0) {
    throw new Error('GET /courses/{courseId}/lessons returned no lessons.')
  }
  const sorted = [...lessons].sort((a, b) => lessonSortKey(a) - lessonSortKey(b))
  for (const lesson of sorted) {
    const id = typeof lesson.id === 'string' ? lesson.id.trim() : ''
    if (id) return id
  }
  throw new Error('GET /courses/{courseId}/lessons returned no lesson ids.')
}

export function pickFirstQuizModuleId(modules) {
  if (!Array.isArray(modules) || modules.length === 0) {
    throw new Error('GET /courses/{courseId}/modules returned no modules.')
  }
  const sorted = [...modules].sort((a, b) => {
    const ao = Number.isFinite(a.order) ? a.order : 0
    const bo = Number.isFinite(b.order) ? b.order : 0
    return ao - bo
  })
  for (const module of sorted) {
    if (module.moduleQuiz) {
      const id = typeof module.id === 'string' ? module.id.trim() : ''
      if (id) return id
    }
  }
  throw new Error(
    'GET /courses/{courseId}/modules returned no module with a quiz (moduleQuiz). Seed the Research Methodology module quiz or sign in as an entitled student.',
  )
}

export function pickFirstAssignmentId(assignments) {
  if (!Array.isArray(assignments) || assignments.length === 0) {
    throw new Error('GET /courses/{courseId}/assignments returned no assignments.')
  }
  for (const assignment of assignments) {
    const id = typeof assignment.id === 'string' ? assignment.id.trim() : ''
    if (id) return id
  }
  throw new Error('GET /courses/{courseId}/assignments returned no assignment ids.')
}

export async function apiGetJson(apiBase, apiPath, bearerToken, fetchImpl = fetch) {
  const url = `${apiBase.replace(/\/+$/, '')}${apiPath.startsWith('/') ? apiPath : `/${apiPath}`}`
  const headers = { Accept: 'application/json' }
  if (bearerToken) headers.Authorization = `Bearer ${bearerToken}`
  const res = await fetchImpl(url, { headers })
  if (!res.ok) {
    throw new Error(`GET ${url} failed with status ${res.status}.`)
  }
  return res.json()
}

/**
 * Resolve a compare page route template to a concrete local path.
 * @param {object} page - PAGES entry from compare-prototype.mjs
 * @param {string} apiBase - prod API base URL
 * @param {object} context
 * @param {string} context.repoRoot
 * @param {string} [context.studentPassword] - required for lesson/quiz/assignment resolve
 * @param {() => Promise<string>} [context.mintStudentIdToken] - Cognito IdToken for student
 * @param {typeof fetch} [context.fetchImpl]
 */
export async function resolveComparePageRoute(page, apiBase, context) {
  const { repoRoot, studentPassword, fetchImpl = fetch } = context
  const mintStudentIdToken = context.mintStudentIdToken

  if (page.resolve === 'credential') {
    const doc = readRs16SeedDocument(repoRoot)
    const credentialId = credentialIdFromSeedDocument(doc)
    return buildVerifyRoute(credentialId)
  }

  if (!page.resolve) return page.route

  const { courses } = await loadCourses(apiBase, fetchImpl)
  const matched = matchPrototypeCourses(courses)
  const course = matched[page.courseKey]
  if (!course) {
    throw new Error(`No prototype course is mapped for ${page.name}.`)
  }

  if (page.resolve === 'course') {
    return `/courses/${encodeURIComponent(course.id)}`
  }

  const needsAuthApi = page.resolve === 'lesson' || page.resolve === 'quiz' || page.resolve === 'assignment'
  if (!needsAuthApi) {
    throw new Error(`Unknown resolve kind "${page.resolve}" for page ${page.name}.`)
  }

  if (!studentPassword) {
    throw new Error(
      'LOCAL_COGNITO_PASSWORD_STUDENT is missing from the repo-root .env.local. Lesson, quiz, and assignment routes need a student API token.',
    )
  }
  if (!mintStudentIdToken) {
    throw new Error('Student Cognito token minting is not configured for compare-prototype route resolution.')
  }

  const token = await mintStudentIdToken()
  const courseId = course.id

  if (page.resolve === 'lesson') {
    const lessons = await apiGetJson(apiBase, `/courses/${courseId}/lessons`, token, fetchImpl)
    if (!Array.isArray(lessons)) {
      throw new Error(`GET /courses/${courseId}/lessons did not return a lesson array.`)
    }
    const lessonId = pickFirstLessonId(lessons)
    return buildLessonRoute(courseId, lessonId)
  }

  if (page.resolve === 'quiz') {
    const modules = await apiGetJson(apiBase, `/courses/${courseId}/modules`, token, fetchImpl)
    if (!Array.isArray(modules)) {
      throw new Error(`GET /courses/${courseId}/modules did not return a module array.`)
    }
    const moduleId = pickFirstQuizModuleId(modules)
    return buildQuizRoute(courseId, moduleId)
  }

  if (page.resolve === 'assignment') {
    const body = await apiGetJson(apiBase, `/courses/${courseId}/assignments`, token, fetchImpl)
    const assignments = Array.isArray(body?.assignments) ? body.assignments : []
    const assignmentId = pickFirstAssignmentId(assignments)
    return buildAssignmentRoute(courseId, assignmentId)
  }

  throw new Error(`Unhandled resolve kind "${page.resolve}" for page ${page.name}.`)
}

/**
 * Resolve lesson/quiz/assignment using the Puppeteer session (one browser sign-in; no admin-initiate-auth).
 * @param {import('puppeteer-core').Page} browserPage
 */
export async function resolveCompareDeepLinkRouteInBrowser(browserPage, page, apiBase, repoRoot) {
  if (page.resolve !== 'lesson' && page.resolve !== 'quiz' && page.resolve !== 'assignment') {
    throw new Error(`resolveCompareDeepLinkRouteInBrowser does not handle resolve=${page.resolve}.`)
  }
  const { courses } = await loadCourses(apiBase)
  const matched = matchPrototypeCourses(courses)
  const course = matched[page.courseKey]
  if (!course) {
    throw new Error(`No prototype course is mapped for ${page.name}.`)
  }
  const courseId = course.id
  const resolveKind = page.resolve

  return browserPage.evaluate(
    async ({ apiBase, courseId, resolveKind }) => {
      function idTokenFromBrowserStorage() {
        for (let i = 0; i < localStorage.length; i += 1) {
          const key = localStorage.key(i)
          if (key && key.endsWith('.idToken')) {
            const value = localStorage.getItem(key)
            if (value && value.trim()) return value.trim()
          }
        }
        return null
      }

      async function browserApiGetJson(apiPath) {
        const token = idTokenFromBrowserStorage()
        if (!token) {
          throw new Error('No Cognito idToken in browser storage.')
        }
        const url = `${apiBase.replace(/\/+$/, '')}${apiPath.startsWith('/') ? apiPath : `/${apiPath}`}`
        const res = await fetch(url, {
          headers: { Accept: 'application/json', Authorization: `Bearer ${token}` },
        })
        if (!res.ok) {
          throw new Error(`GET ${url} failed with status ${res.status}.`)
        }
        return res.json()
      }

      function lessonSortKey(lesson) {
        const moduleOrder = Number.isFinite(lesson.moduleOrder) ? lesson.moduleOrder : 0
        const order = Number.isFinite(lesson.order) ? lesson.order : 0
        return moduleOrder * 10000 + order
      }

      function pickFirstLessonId(lessons) {
        const sorted = [...lessons].sort((a, b) => lessonSortKey(a) - lessonSortKey(b))
        for (const lesson of sorted) {
          const id = typeof lesson.id === 'string' ? lesson.id.trim() : ''
          if (id) return id
        }
        throw new Error('No lesson ids in API response.')
      }

      function pickFirstQuizModuleId(modules) {
        const sorted = [...modules].sort((a, b) => {
          const ao = Number.isFinite(a.order) ? a.order : 0
          const bo = Number.isFinite(b.order) ? b.order : 0
          return ao - bo
        })
        for (const module of sorted) {
          if (module.moduleQuiz) {
            const id = typeof module.id === 'string' ? module.id.trim() : ''
            if (id) return id
          }
        }
        throw new Error('No module with moduleQuiz in API response.')
      }

      function pickFirstAssignmentId(assignments) {
        for (const assignment of assignments) {
          const id = typeof assignment.id === 'string' ? assignment.id.trim() : ''
          if (id) return id
        }
        throw new Error('No assignment ids in API response.')
      }

      const enc = (value) => encodeURIComponent(value)

      if (resolveKind === 'lesson') {
        const lessons = await browserApiGetJson(`/courses/${courseId}/lessons`)
        if (!Array.isArray(lessons)) throw new Error('Lessons response was not an array.')
        const lessonId = pickFirstLessonId(lessons)
        return `/courses/${enc(courseId)}/lessons/${enc(lessonId)}`
      }
      if (resolveKind === 'quiz') {
        const modules = await browserApiGetJson(`/courses/${courseId}/modules`)
        if (!Array.isArray(modules)) throw new Error('Modules response was not an array.')
        const moduleId = pickFirstQuizModuleId(modules)
        return `/courses/${enc(courseId)}/modules/${enc(moduleId)}/quiz`
      }
      const body = await browserApiGetJson(`/courses/${courseId}/assignments`)
      const assignments = Array.isArray(body?.assignments) ? body.assignments : []
      const assignmentId = pickFirstAssignmentId(assignments)
      return `/courses/${enc(courseId)}/assignments/${enc(assignmentId)}`
    },
    { apiBase, courseId, resolveKind: page.resolve },
  )
}

export async function cfnOutputValue({ stackName, outputKey, region, execFileAsync, awsExecutable }) {
  const { stdout } = await execFileAsync(
    awsExecutable,
    [
      'cloudformation',
      'describe-stacks',
      '--stack-name',
      stackName,
      '--region',
      region,
      '--query',
      `Stacks[0].Outputs[?OutputKey=='${outputKey}'].OutputValue | [0]`,
      '--output',
      'text',
      '--no-cli-pager',
    ],
    { windowsHide: true },
  )
  const value = stdout.trim()
  if (!value || value === 'None') {
    throw new Error(`Could not resolve ${outputKey} from ${stackName} in ${region}.`)
  }
  return value
}

const VITE_ENV_FILES = ['.env', '.env.local', '.env.production', '.env.production.local']

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

/** Cognito SPA vars from frontend/.env* and process.env (same layering as Vite production build). */
export function readStudentCognitoViteEnv(frontendDir) {
  const merged = {}
  for (const name of VITE_ENV_FILES) {
    Object.assign(merged, parseEnvFile(path.join(frontendDir, name)))
  }
  const pick = (key) => {
    const fromProc = process.env[key]
    if (fromProc !== undefined && String(fromProc).trim() !== '') return String(fromProc).trim()
    return String(merged[key] ?? '').trim()
  }
  return {
    VITE_COGNITO_USER_POOL_ID: pick('VITE_COGNITO_USER_POOL_ID'),
    VITE_COGNITO_USER_POOL_CLIENT_ID: pick('VITE_COGNITO_USER_POOL_CLIENT_ID'),
    VITE_COGNITO_DOMAIN: pick('VITE_COGNITO_DOMAIN'),
  }
}

export function cognitoViteEnvComplete(env) {
  return Boolean(
    env.VITE_COGNITO_USER_POOL_ID &&
      env.VITE_COGNITO_USER_POOL_CLIENT_ID &&
      env.VITE_COGNITO_DOMAIN,
  )
}

/** Prod student SPA Cognito from StreamMyCourse-Auth-prod when local Vite env is incomplete. */
export async function resolveStudentCognitoViteEnv({
  frontendDir,
  authStack = DEFAULT_AUTH_STACK,
  region = process.env.AWS_REGION || process.env.AWS_DEFAULT_REGION || 'eu-west-1',
  execFileAsync,
  awsExecutable,
  /** Compare must match deployed prod; ignore stale frontend/.env* client ids. */
  preferAuthStack = false,
}) {
  if (!preferAuthStack) {
    const fromFiles = readStudentCognitoViteEnv(frontendDir)
    if (cognitoViteEnvComplete(fromFiles)) return fromFiles
  }
  const userPoolId = await cfnOutputValue({
    stackName: authStack,
    outputKey: 'UserPoolId',
    region,
    execFileAsync,
    awsExecutable,
  })
  const clientId = await cfnOutputValue({
    stackName: authStack,
    outputKey: 'StudentUserPoolClientId',
    region,
    execFileAsync,
    awsExecutable,
  })
  const domain = await cfnOutputValue({
    stackName: authStack,
    outputKey: 'HostedUIDomain',
    region,
    execFileAsync,
    awsExecutable,
  })
  console.log(
    `Student compare build uses ${authStack} Cognito (pool + StudentUserPoolClientId + HostedUIDomain).`,
  )
  return {
    VITE_COGNITO_USER_POOL_ID: userPoolId,
    VITE_COGNITO_USER_POOL_CLIENT_ID: clientId,
    VITE_COGNITO_DOMAIN: domain,
  }
}

/** Mint student IdToken via cognito-idp admin-initiate-auth (same flow as integration tests). */
export async function mintStudentIdTokenViaAws({
  password,
  email = DEFAULT_STUDENT_EMAIL,
  authStack = DEFAULT_AUTH_STACK,
  region = process.env.AWS_REGION || process.env.AWS_DEFAULT_REGION || 'eu-west-1',
  execFileAsync,
  awsExecutable,
}) {
  if (!password) {
    throw new Error('Student password is required to mint a Cognito token.')
  }
  const userPoolId = await cfnOutputValue({
    stackName: authStack,
    outputKey: 'UserPoolId',
    region,
    execFileAsync,
    awsExecutable,
  })
  const clientId = await cfnOutputValue({
    stackName: authStack,
    outputKey: 'StudentUserPoolClientId',
    region,
    execFileAsync,
    awsExecutable,
  })
  const authJson = JSON.stringify({
    UserPoolId: userPoolId,
    ClientId: clientId,
    AuthFlow: 'ADMIN_USER_PASSWORD_AUTH',
    AuthParameters: {
      USERNAME: email,
      PASSWORD: password,
    },
  })
  const { stdout } = await execFileAsync(
    awsExecutable,
    [
      'cognito-idp',
      'admin-initiate-auth',
      '--cli-input-json',
      authJson,
      '--region',
      region,
      '--query',
      'AuthenticationResult.IdToken',
      '--output',
      'text',
      '--no-cli-pager',
    ],
    { windowsHide: true },
  )
  const token = stdout.trim()
  if (!token || token === 'None') {
    throw new Error(
      `Failed to mint Cognito IdToken for ${email}. Check LOCAL_COGNITO_PASSWORD_STUDENT and AWS credentials for ${authStack}.`,
    )
  }
  return token
}
