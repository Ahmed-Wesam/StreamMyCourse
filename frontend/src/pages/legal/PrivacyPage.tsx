import { privacyAr } from '../../lib/legal/content/privacy.ar'
import { privacyEn } from '../../lib/legal/content/privacy.en'
import { LegalDocumentPage } from './LegalDocumentPage'

export default function PrivacyPage() {
  return <LegalDocumentPage english={privacyEn} arabic={privacyAr} />
}
