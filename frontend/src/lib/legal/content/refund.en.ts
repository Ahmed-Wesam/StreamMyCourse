import { legalConfig } from '../../legalConfig'
import type { LegalDocumentContent } from './types'

const { supportEmail } = legalConfig

export const refundEn: LegalDocumentContent = {
  title: 'Refund & Cancellation Policy',
  lastUpdated: '2026-06-01',
  sections: [
    {
      heading: 'Introduction',
      paragraphs: [
        'Research Spectrum is committed to providing high-quality educational content and learning experiences. Because our products consist primarily of digital educational content that is delivered immediately upon purchase, this Refund & Cancellation Policy governs all purchases made through the Research Spectrum platform.',
        'By purchasing any course, course bundle, educational resource, certification pathway, or related offering currently made available through Research Spectrum, you acknowledge and agree to this policy.',
      ],
    },
    {
      heading: 'Digital Product Nature',
      paragraphs: [
        'Research Spectrum provides digital educational products and services that become accessible immediately upon successful payment.',
        'Because access is granted instantly and digital content may be consumed immediately, all purchases are considered final.',
      ],
    },
    {
      heading: 'No Refund Policy',
      paragraphs: [
        'Except where required by applicable law, all purchases made through Research Spectrum are non-refundable.',
        'This includes, but is not limited to:',
        '• Individual courses',
        '• Course bundles',
        '• Complete learning pathways',
        '• Certifications',
        '• Digital resources',
        'Refunds will not be issued because:',
        '• A user changed their mind.',
        '• A user no longer has time to complete the course.',
        '• A user misunderstood the course description.',
        '• A user failed an assessment.',
        '• A user did not obtain a certificate.',
        '• A user did not achieve a desired academic or professional outcome.',
        '• A user did not secure publication, funding, employment, residency placement, academic acceptance, or other opportunities.',
        '• A user failed to complete the course.',
        '• A user disagrees with teaching methods or presentation style.',
        '• A user purchased the wrong course.',
        '• A user did not review the course information before purchase.',
      ],
    },
    {
      heading: 'Course Access After Purchase',
      paragraphs: [
        'Upon successful payment, users receive access to purchased content. Access to purchased content remains available in accordance with the Terms & Conditions and applicable platform access policies.',
        'Access to digital content constitutes fulfillment of Research Spectrum\'s delivery obligations.',
      ],
    },
    {
      heading: 'Fraudulent Purchases',
      paragraphs: [
        'Research Spectrum reserves the right, subject to the Terms & Conditions, to:',
        '• Suspend access',
        '• Revoke certificates',
        '• Cancel enrollments',
        '• Terminate accounts',
        'where purchases are suspected to involve:',
        '• Stolen payment methods',
        '• Unauthorized transactions',
        '• Fraudulent activity',
        '• Chargeback abuse',
        '• Payment manipulation',
        'No refunds will be issued for accounts terminated due to fraud or policy violations.',
      ],
    },
    {
      heading: 'Chargebacks and Payment Disputes',
      paragraphs: [
        'Initiating a chargeback, payment dispute, reversal, or similar claim after receiving access to digital content may result in, subject to the Terms & Conditions:',
        '• Immediate suspension of access',
        '• Account termination',
        '• Certificate revocation',
        '• Loss of access to all purchased content',
        'Research Spectrum reserves the right to challenge fraudulent or abusive chargebacks and provide supporting documentation to payment processors.',
      ],
    },
    {
      heading: 'Cancellation of Services',
      paragraphs: [
        'Research Spectrum does not currently operate on a subscription model.',
        'As a result:',
        '• There are no recurring subscription charges to cancel.',
        '• Purchased courses remain available in accordance with the Terms & Conditions.',
        '• Users may discontinue use of the platform at any time.',
        '• Discontinuing use does not create eligibility for a refund.',
      ],
    },
    {
      heading: 'Future Services',
      paragraphs: [
        'Research Spectrum may introduce subscription products, workshops, mentorship programs, consultations, live educational events, or other services in the future.',
        'Separate refund and cancellation terms may apply to such offerings and will be published at the time those services become available.',
        'Research Spectrum reserves the right to publish additional policies governing any future products or services.',
      ],
    },
    {
      heading: 'Exceptional Circumstances',
      paragraphs: [
        'Where required by applicable law, Research Spectrum may provide remedies, refunds, or other resolutions as legally required.',
        'Any such remedy shall be determined in accordance with applicable legal obligations.',
        'Nothing in this policy limits rights that cannot legally be excluded under applicable law.',
      ],
    },
    {
      heading: 'Policy Changes',
      paragraphs: [
        'Research Spectrum reserves the right to modify this Refund & Cancellation Policy at any time.',
        'Updated versions will be published on the website.',
        'Continued use of Research Spectrum Services following publication of updated policies constitutes acceptance of the revised policy.',
        'Research Spectrum may additionally notify users of significant changes via email.',
      ],
    },
    {
      heading: 'Language',
      paragraphs: [
        'This policy may be provided in multiple languages.',
        'In the event of any discrepancy, inconsistency, conflict, or ambiguity between language versions, the English version shall prevail.',
      ],
    },
    {
      heading: 'Contact',
      paragraphs: [
        'For questions regarding this Refund & Cancellation Policy, please contact:',
        'For inquiries: ' + supportEmail,
      ],
    },
  ],
}
