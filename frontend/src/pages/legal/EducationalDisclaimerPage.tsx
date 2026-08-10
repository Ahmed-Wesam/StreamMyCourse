import { educationalDisclaimerAr } from '../../lib/legal/content/educational-disclaimer.ar'
import { educationalDisclaimerEn } from '../../lib/legal/content/educational-disclaimer.en'
import { LegalDocumentPage } from './LegalDocumentPage'

export default function EducationalDisclaimerPage() {
  return (
    <LegalDocumentPage english={educationalDisclaimerEn} arabic={educationalDisclaimerAr} />
  )
}
