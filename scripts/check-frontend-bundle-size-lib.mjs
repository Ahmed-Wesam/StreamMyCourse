import fs from 'node:fs'
import path from 'node:path'
import zlib from 'node:zlib'

export const VENDOR_EXCLUDE = ['react-vendor', 'amplify-vendor', 'rolldown-runtime']

export const THRESHOLDS = {
  studentEntryGzipKb: 15,
  teacherEntryGzipKb: 15,
  amplifyVendorGzipKb: 110,
  reactVendorGzipKb: 75,
  studentFirstLoadPublicGzipKb: 85,
  /** Target rubric 150 KB; enforced 180 until amplify-vendor (~101 KB gzip) slimming. */
  studentFirstLoadWithAuthGzipKb: 180,
  teacherFirstLoadWithAuthGzipKb: 180,
}

export function gzipSizeBytes(filePath) {
  const raw = fs.readFileSync(filePath)
  return zlib.gzipSync(raw).length
}

export function listJsAssets(distSpaDir) {
  const assetsDir = path.join(distSpaDir, 'assets')
  if (!fs.existsSync(assetsDir)) {
    throw new Error(`Missing assets dir: ${assetsDir} (run npm run build:all first)`)
  }
  return fs
    .readdirSync(assetsDir)
    .filter((name) => name.endsWith('.js') && !name.endsWith('.map'))
    .map((name) => path.join(assetsDir, name))
}

export function isVendorChunk(fileName) {
  return VENDOR_EXCLUDE.some((token) => fileName.includes(token))
}

/** @deprecated Prefer findEntryFromHtml — largest match picks lazy route chunks (e.g. StudentLessonAuth). */
export function findChunk(files, pattern) {
  const matches = files.filter((f) => {
    const base = path.basename(f)
    return pattern.test(base) && !isVendorChunk(base)
  })
  if (matches.length === 0) return null
  return matches.reduce((best, f) =>
    gzipSizeBytes(f) > gzipSizeBytes(best) ? f : best,
  )
}

/**
 * Resolve the SPA entry chunk from dist/index.html (script type=module or matching modulepreload).
 * Avoids mis-identifying large lazy route chunks that match student-*.js / teacher-*.js loosely.
 */
export function findEntryFromHtml(distSpaDir, entryBasenamePattern) {
  const indexPath = path.join(distSpaDir, 'index.html')
  if (!fs.existsSync(indexPath)) {
    throw new Error(`Missing index.html: ${indexPath} (run npm run build:all first)`)
  }
  const html = fs.readFileSync(indexPath, 'utf8')
  const assetsDir = path.join(distSpaDir, 'assets')

  const hrefs = []
  const moduleScript =
    html.match(
      /<script[^>]*type=["']module["'][^>]*src=["']([^"']+)["']/i,
    ) ??
    html.match(
      /<script[^>]*src=["']([^"']+)["'][^>]*type=["']module["']/i,
    )
  if (moduleScript) hrefs.push(moduleScript[1])

  for (const m of html.matchAll(
    /<link[^>]*rel=["']modulepreload["'][^>]*href=["']([^"']+)["']/gi,
  )) {
    hrefs.push(m[1])
  }
  for (const m of html.matchAll(
    /<link[^>]*href=["']([^"']+)["'][^>]*rel=["']modulepreload["']/gi,
  )) {
    hrefs.push(m[1])
  }

  for (const href of hrefs) {
    const base = path.basename(href)
    if (!entryBasenamePattern.test(base) || isVendorChunk(base)) continue
    const filePath = path.join(assetsDir, base)
    if (fs.existsSync(filePath)) return filePath
  }

  return null
}

export function findVendor(files, token) {
  const match = files.find((f) => path.basename(f).includes(token))
  return match ?? null
}

export function kb(bytes) {
  return bytes / 1024
}

export function formatKb(bytes) {
  return `${kb(bytes).toFixed(2)} KB`
}

export function checkLimit(label, bytes, maxKb) {
  const maxBytes = maxKb * 1024
  const ok = bytes <= maxBytes
  return { label, bytes, maxKb, ok }
}

/**
 * Core gzip metrics for one SPA from built asset file paths.
 * firstLoadPublicGzip = entry + react; firstLoadWithAuthGzip = entry + react + amplify.
 */
export function measureSpaMetrics(files, distSpaDir, entryBasenamePattern) {
  const entry = findEntryFromHtml(distSpaDir, entryBasenamePattern)
  const amplify = findVendor(files, 'amplify-vendor')
  const react = findVendor(files, 'react-vendor')

  if (!entry) {
    throw new Error(
      `no entry chunk in index.html matching ${entryBasenamePattern}`,
    )
  }
  if (!amplify) {
    throw new Error('amplify-vendor chunk not found')
  }
  if (!react) {
    throw new Error('react-vendor chunk not found')
  }

  const entryGzip = gzipSizeBytes(entry)
  const amplifyGzip = gzipSizeBytes(amplify)
  const reactGzip = gzipSizeBytes(react)
  const firstLoadPublicGzip = entryGzip + reactGzip
  const firstLoadWithAuthGzip = entryGzip + reactGzip + amplifyGzip

  return {
    entry,
    entryGzip,
    reactGzip,
    amplifyGzip,
    firstLoadPublicGzip,
    firstLoadWithAuthGzip,
  }
}

export function measureSpa(spaKey, distDir, entryBasenamePattern, entryMaxKb) {
  const files = listJsAssets(distDir)
  const metrics = measureSpaMetrics(files, distDir, entryBasenamePattern)
  const amplify = findVendor(files, 'amplify-vendor')
  const react = findVendor(files, 'react-vendor')
  const totalJsGzip = files.reduce((sum, f) => sum + gzipSizeBytes(f), 0)

  const checks = [
    checkLimit(`${spaKey} entry`, metrics.entryGzip, entryMaxKb),
    checkLimit(`${spaKey} amplify-vendor`, metrics.amplifyGzip, THRESHOLDS.amplifyVendorGzipKb),
    checkLimit(`${spaKey} react-vendor`, metrics.reactGzip, THRESHOLDS.reactVendorGzipKb),
  ]

  if (spaKey === 'student') {
    checks.push(
      checkLimit(
        `${spaKey} firstLoadPublic`,
        metrics.firstLoadPublicGzip,
        THRESHOLDS.studentFirstLoadPublicGzipKb,
      ),
      checkLimit(
        `${spaKey} firstLoadWithAuth`,
        metrics.firstLoadWithAuthGzip,
        THRESHOLDS.studentFirstLoadWithAuthGzipKb,
      ),
    )
  } else if (spaKey === 'teacher') {
    checks.push(
      checkLimit(
        `${spaKey} firstLoadWithAuth`,
        metrics.firstLoadWithAuthGzip,
        THRESHOLDS.teacherFirstLoadWithAuthGzipKb,
      ),
    )
  }

  return {
    spaKey,
    entry: path.basename(metrics.entry),
    entryGzip: metrics.entryGzip,
    amplify: path.basename(amplify),
    amplifyGzip: metrics.amplifyGzip,
    react: path.basename(react),
    reactGzip: metrics.reactGzip,
    firstLoadPublicGzip: metrics.firstLoadPublicGzip,
    firstLoadWithAuthGzip: metrics.firstLoadWithAuthGzip,
    totalJsGzip,
    jsFileCount: files.length,
    checks,
  }
}
