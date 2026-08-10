import { termsEn } from '../../lib/legal/content/terms.en'
import { LegalDocumentPage } from './LegalDocumentPage'

export default function TermsPage() {
  return <LegalDocumentPage content={termsEn} />
}
