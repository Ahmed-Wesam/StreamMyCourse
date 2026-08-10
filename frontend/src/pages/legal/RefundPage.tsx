import { refundAr } from '../../lib/legal/content/refund.ar'
import { refundEn } from '../../lib/legal/content/refund.en'
import { LegalDocumentPage } from './LegalDocumentPage'

export default function RefundPage() {
  return <LegalDocumentPage english={refundEn} arabic={refundAr} />
}
