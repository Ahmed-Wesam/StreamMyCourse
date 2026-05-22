#!/usr/bin/env node
/**
 * Guard production bundle sizes after `npm run build:all`.
 * Expects frontend/dist/student and frontend/dist/teacher.
 *
 * Usage (from frontend/): node ../scripts/check-frontend-bundle-size.mjs [--dry-run]
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  THRESHOLDS,
  formatKb,
  measureSpa,
} from './check-frontend-bundle-size-lib.mjs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, '..')
const frontendDir = path.join(repoRoot, 'frontend')

const dryRun = process.argv.includes('--dry-run')

/** Entry basename from index.html script/modulepreload (not largest student-*.js). */
const STUDENT_ENTRY_PATTERN = /^student-[A-Za-z0-9_-]+\.js$/
const TEACHER_ENTRY_PATTERN = /^teacher-[A-Za-z0-9_-]+\.js$/

function findWebpBytes() {
  for (const sub of ['student', 'teacher']) {
    const assetsDir = path.join(frontendDir, 'dist', sub, 'assets')
    if (!fs.existsSync(assetsDir)) continue
    const webp = fs
      .readdirSync(assetsDir)
      .find((name) => name.endsWith('.webp') && name.includes('dr-bahaa'))
    if (webp) {
      const filePath = path.join(assetsDir, webp)
      return { name: webp, bytes: fs.statSync(filePath).size, spa: sub }
    }
  }
  const srcWebp = path.join(
    frontendDir,
    'src/assets/instructors/dr-bahaa-aburayya.webp',
  )
  if (fs.existsSync(srcWebp)) {
    return { name: 'dr-bahaa-aburayya.webp (src)', bytes: fs.statSync(srcWebp).size, spa: 'src' }
  }
  return null
}

function printReport(student, teacher, webp) {
  const rows = [
    ['Metric', 'Student', 'Teacher'],
    ['Entry chunk', student.entry, teacher.entry],
    ['Entry gzip', formatKb(student.entryGzip), formatKb(teacher.entryGzip)],
    [
      'firstLoadPublic gzip',
      formatKb(student.firstLoadPublicGzip),
      '—',
    ],
    [
      'firstLoadWithAuth gzip',
      formatKb(student.firstLoadWithAuthGzip),
      formatKb(teacher.firstLoadWithAuthGzip),
    ],
    ['amplify-vendor gzip', formatKb(student.amplifyGzip), formatKb(teacher.amplifyGzip)],
    ['react-vendor gzip', formatKb(student.reactGzip), formatKb(teacher.reactGzip)],
    ['Total JS gzip (all chunks)', formatKb(student.totalJsGzip), formatKb(teacher.totalJsGzip)],
    ['JS chunk count', String(student.jsFileCount), String(teacher.jsFileCount)],
  ]
  const colWidths = rows[0].map((_, i) => Math.max(...rows.map((r) => r[i].length)))
  for (const row of rows) {
    console.log(row.map((cell, i) => cell.padEnd(colWidths[i])).join('  '))
  }
  if (webp) {
    console.log(`\nInstructor WebP (${webp.spa}): ${webp.name} — ${webp.bytes} bytes (${formatKb(webp.bytes)})`)
  } else {
    console.log('\nInstructor WebP: not found in dist (optional metric)')
  }
  console.log('\nThresholds (gzip):')
  console.log(
    `  firstLoadPublic: ${THRESHOLDS.studentFirstLoadPublicGzipKb} KB (student)`,
  )
  console.log(
    `  firstLoadWithAuth: ${THRESHOLDS.studentFirstLoadWithAuthGzipKb} KB (student), ${THRESHOLDS.teacherFirstLoadWithAuthGzipKb} KB (teacher)`,
  )
  console.log(`  entry: ${THRESHOLDS.studentEntryGzipKb} KB (student), ${THRESHOLDS.teacherEntryGzipKb} KB (teacher)`)
  console.log(`  amplify-vendor: ${THRESHOLDS.amplifyVendorGzipKb} KB (each SPA)`)
  console.log(`  react-vendor: ${THRESHOLDS.reactVendorGzipKb} KB (each SPA)`)
  if (dryRun) {
    console.log('\n--dry-run: thresholds not enforced')
  }
}

function main() {
  const student = measureSpa(
    'student',
    path.join(frontendDir, 'dist', 'student'),
    STUDENT_ENTRY_PATTERN,
    THRESHOLDS.studentEntryGzipKb,
  )
  const teacher = measureSpa(
    'teacher',
    path.join(frontendDir, 'dist', 'teacher'),
    TEACHER_ENTRY_PATTERN,
    THRESHOLDS.teacherEntryGzipKb,
  )
  const webp = findWebpBytes()

  printReport(student, teacher, webp)

  const failures = [...student.checks, ...teacher.checks].filter((c) => !c.ok)
  if (dryRun) {
    process.exit(0)
  }
  if (failures.length > 0) {
    console.error('\nBundle size guard FAILED:')
    for (const f of failures) {
      console.error(
        `  ${f.label}: ${formatKb(f.bytes)} exceeds max ${f.maxKb} KB`,
      )
    }
    process.exit(1)
  }
  console.log('\nBundle size guard: OK')
  process.exit(0)
}

const isMain =
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)

if (isMain) {
  try {
    main()
  } catch (err) {
    console.error(`check-frontend-bundle-size: ${err.message}`)
    process.exit(1)
  }
}
