import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { test } from 'node:test'
import {
  checkLimit,
  findEntryFromHtml,
  gzipSizeBytes,
  measureSpaMetrics,
} from './check-frontend-bundle-size-lib.mjs'

function mkFixtureAssets() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'bundle-fixture-'))
  const assetsDir = path.join(root, 'assets')
  fs.mkdirSync(assetsDir, { recursive: true })

  const write = (name, body) => {
    const filePath = path.join(assetsDir, name)
    fs.writeFileSync(filePath, body)
    return filePath
  }

  const entryPath = write('student-entry.js', 'entry-chunk-payload-'.repeat(40))
  write(
    'StudentLessonAuth-huge.js',
    'lazy-route-chunk-payload-'.repeat(200),
  )
  const reactPath = write('react-vendor-abc.js', 'react-vendor-payload-'.repeat(30))
  const amplifyPath = write('amplify-vendor-xyz.js', 'amplify-vendor-payload-'.repeat(50))
  write('rolldown-runtime.js', 'runtime-'.repeat(10))

  fs.writeFileSync(
    path.join(root, 'index.html'),
    `<!doctype html>
<html><head>
<script type="module" crossorigin src="/assets/student-entry.js"></script>
<link rel="modulepreload" crossorigin href="/assets/react-vendor-abc.js">
<link rel="modulepreload" crossorigin href="/assets/amplify-vendor-xyz.js">
</head><body></body></html>`,
  )

  const files = fs
    .readdirSync(assetsDir)
    .filter((n) => n.endsWith('.js'))
    .map((n) => path.join(assetsDir, n))
  const entryGzip = gzipSizeBytes(entryPath)
  const reactGzip = gzipSizeBytes(reactPath)
  const amplifyGzip = gzipSizeBytes(amplifyPath)

  return {
    root,
    files,
    entryGzip,
    reactGzip,
    amplifyGzip,
    expectedPublic: entryGzip + reactGzip,
    expectedWithAuth: entryGzip + reactGzip + amplifyGzip,
  }
}

test('findEntryFromHtml picks index.html script, not largest student-*.js', () => {
  const fx = mkFixtureAssets()
  try {
    const entry = findEntryFromHtml(fx.root, /^student-[A-Za-z0-9_-]+\.js$/)
    assert.ok(entry)
    assert.equal(path.basename(entry), 'student-entry.js')
  } finally {
    fs.rmSync(fx.root, { recursive: true, force: true })
  }
})

test('measureSpaMetrics computes firstLoadPublicGzip as entry + react', () => {
  const fx = mkFixtureAssets()
  try {
    const metrics = measureSpaMetrics(
      fx.files,
      fx.root,
      /^student-[A-Za-z0-9_-]+\.js$/,
    )
    assert.equal(metrics.entryGzip, fx.entryGzip)
    assert.equal(metrics.reactGzip, fx.reactGzip)
    assert.equal(metrics.firstLoadPublicGzip, fx.expectedPublic)
  } finally {
    fs.rmSync(fx.root, { recursive: true, force: true })
  }
})

test('measureSpaMetrics computes firstLoadWithAuthGzip as entry + react + amplify', () => {
  const fx = mkFixtureAssets()
  try {
    const metrics = measureSpaMetrics(
      fx.files,
      fx.root,
      /^student-[A-Za-z0-9_-]+\.js$/,
    )
    assert.equal(metrics.amplifyGzip, fx.amplifyGzip)
    assert.equal(metrics.firstLoadWithAuthGzip, fx.expectedWithAuth)
  } finally {
    fs.rmSync(fx.root, { recursive: true, force: true })
  }
})

test('checkLimit fails when bytes exceed maxKb threshold', () => {
  const overBytes = 20 * 1024
  const result = checkLimit('fixture entry', overBytes, 15)
  assert.equal(result.ok, false)
  assert.equal(result.maxKb, 15)
  assert.equal(result.bytes, overBytes)
})

test('checkLimit passes when bytes are within maxKb threshold', () => {
  const underBytes = 10 * 1024
  const result = checkLimit('fixture entry', underBytes, 15)
  assert.equal(result.ok, true)
})
