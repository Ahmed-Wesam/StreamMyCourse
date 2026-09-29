/**
 * @vitest-environment node
 */
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const DIR = dirname(fileURLToPath(import.meta.url))

describe('teacher-certificates jspdf guard', () => {
  it('TeacherCourseCertificates source does not include jspdf', () => {
    const source = readFileSync(join(DIR, 'TeacherCourseCertificates.tsx'), 'utf8')
    expect(source).not.toMatch(/jspdf/i)
    expect(source).not.toMatch(/certificatePdf/)
  })
})
