import { describe, expect, it } from 'vitest'

import { contentTypeForLessonFileType, fileTypeFromFileName } from './lessonFileType'

describe('fileTypeFromFileName', () => {
  it('maps supported extensions', () => {
    expect(fileTypeFromFileName('notes.PDF')).toBe('pdf')
    expect(fileTypeFromFileName('data.csv')).toBe('csv')
    expect(fileTypeFromFileName('sheet.xlsx')).toBe('xlsx')
  })

  it('rejects unknown extensions', () => {
    expect(() => fileTypeFromFileName('virus.exe')).toThrow(/unsupported/i)
  })
})

describe('contentTypeForLessonFileType', () => {
  it('returns catalog content types', () => {
    expect(contentTypeForLessonFileType('pdf')).toBe('application/pdf')
    expect(contentTypeForLessonFileType('csv')).toBe('text/csv')
  })
})
