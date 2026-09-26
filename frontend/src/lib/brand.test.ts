/**
 * Scans production frontend sources for the retired user-visible brand string.
 * "StreamMyCourse" (repo/stack names) is intentionally allowed.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { dirname, join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

/** Built so this test file itself never contains the retired brand literal. */
const FORBIDDEN = ['SPSS', 'Spectrum'].join(' ')

const libDir = dirname(fileURLToPath(import.meta.url))
const srcRoot = join(libDir, '..')
const frontendRoot = join(srcRoot, '..')

function collectSourceFiles(dir: string, out: string[]): void {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    const st = statSync(full)
    if (st.isDirectory()) {
      collectSourceFiles(full, out)
      continue
    }
    if (name.endsWith('.ts') || name.endsWith('.tsx')) {
      out.push(full)
    }
  }
}

function findForbiddenOccurrences(): string[] {
  const files: string[] = []
  collectSourceFiles(srcRoot, files)
  for (const htmlName of ['index.html', 'student.html', 'teacher.html'] as const) {
    files.push(join(frontendRoot, htmlName))
  }

  const hits: string[] = []
  for (const file of files) {
    const text = readFileSync(file, 'utf8')
    if (!text.includes(FORBIDDEN)) continue
    const rel = relative(frontendRoot, file).replace(/\\/g, '/')
    hits.push(rel)
  }
  return hits
}

describe('brand string scan', () => {
  it(`has no user-visible "${FORBIDDEN}" in src or HTML entry files`, () => {
    const hits = findForbiddenOccurrences()
    expect(hits, `Unexpected "${FORBIDDEN}" in:\n${hits.join('\n')}`).toEqual([])
  })
})
