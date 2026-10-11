import { usePageTitle } from '../lib/page-title'

/** Pricing controls are offline while payments are rebuilt. */
export default function TeacherPaymentSetup() {
  usePageTitle('Pricing')
  return (
    <div data-testid="teacher-payment-setup">
      <h1>Pricing is closed</h1>
      <p>Course prices are not being changed while checkout is rebuilt.</p>
    </div>
  )
}
