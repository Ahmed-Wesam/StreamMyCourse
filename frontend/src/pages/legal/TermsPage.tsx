import { termsAr } from '../../lib/legal/content/terms.ar'
import { termsEn } from '../../lib/legal/content/terms.en'
import { LegalDocumentPage } from './LegalDocumentPage'

export default function TermsPage() {
  return <LegalDocumentPage english={termsEn} arabic={termsAr} />
}
