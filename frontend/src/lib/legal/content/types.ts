type LegalSection = {
  heading: string
  paragraphs: string[]
}

export type LegalDocumentContent = {
  title: string
  lastUpdated: string
  sections: LegalSection[]
}
