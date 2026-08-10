import type { LegalDocumentContent } from './types'

/** Placeholder until counsel-approved Arabic translations of the June 2026 legal pack ship. */
export function arabicLegalPending(titleAr: string): LegalDocumentContent {
  return {
    title: titleAr,
    lastUpdated: '2026-06-01',
    sections: [
      {
        heading: 'النسخة العربية',
        paragraphs: [
          'النسخة الإنجليزية من هذه الوثيقة هي النسخة المعتمدة والكاملة حالياً. يُرجى اختيار English أعلاه لقراءة النص القانوني الساري.',
          'في حال وجود أي تعارض أو اختلاف بين النسختين، تسود النسخة الإنجليزية وفقاً لسياسات Research Spectrum.',
        ],
      },
    ],
  }
}
