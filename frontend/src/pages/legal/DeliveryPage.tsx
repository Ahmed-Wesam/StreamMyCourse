import { deliveryAr } from '../../lib/legal/content/delivery.ar'
import { deliveryEn } from '../../lib/legal/content/delivery.en'
import { LegalDocumentPage } from './LegalDocumentPage'

export default function DeliveryPage() {
  return <LegalDocumentPage english={deliveryEn} arabic={deliveryAr} />
}
