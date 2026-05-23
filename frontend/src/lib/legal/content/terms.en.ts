import { legalConfig } from '../../legalConfig'
import type { LegalDocumentContent } from './types'

const {
  legalEntityNameEn,
  brandDisplayName,
  supportEmail,
  websiteHost,
  governingLaw,
} = legalConfig

export const termsEn: LegalDocumentContent = {
  title: 'Terms and Conditions',
  lastUpdated: '2026-05-23',
  sections: [
    {
      heading: '1. Agreement',
      paragraphs: [
        `These Terms and Conditions ("Terms") apply to your use of ${brandDisplayName} at ${websiteHost}, operated by ${legalEntityNameEn}. By creating an account, subscribing, or using the service, you agree to these Terms. If you do not agree, do not use ${brandDisplayName}.`,
      ],
    },
    {
      heading: '2. The service',
      paragraphs: [
        `${brandDisplayName} provides online courses and related learning features. Access to published courses requires an active monthly subscription unless we state otherwise on the site.`,
      ],
    },
    {
      heading: '3. Subscriptions and payment',
      paragraphs: [
        'Subscriptions are billed monthly in Jordanian dinar (JOD). The current price is shown on the site before you subscribe.',
        `${legalEntityNameEn} is the seller of your subscription. Payments are processed by our payment provider (PayTabs). We do not store your full card number on our servers.`,
        'Subscriptions renew automatically each billing period until you cancel. We may change prices or payment methods with reasonable notice on the site or by email. Continued use after a price change constitutes acceptance unless you cancel before the next billing date.',
      ],
    },
    {
      heading: '4. Cancellation and refunds',
      paragraphs: [
        'You may cancel from your account subscription page at any time. Cancellation takes effect at the end of the current paid billing period. You keep access until that date.',
        'Fees are generally non-refundable for partial billing periods unless required by applicable law.',
      ],
    },
    {
      heading: '5. Your account',
      paragraphs: [
        'You sign in with Google. You are responsible for your account activity and for keeping access to your Google account secure.',
        `Provide accurate information and notify us at ${supportEmail} if you believe your account has been used without permission.`,
      ],
    },
    {
      heading: '6. Acceptable use',
      paragraphs: [
        'Use course content for personal learning only. Do not copy, redistribute, resell, reverse engineer, or attempt to bypass access controls.',
        'We may suspend or terminate access for breach of these Terms, fraud, or abuse.',
      ],
    },
    {
      heading: '7. Intellectual property',
      paragraphs: [
        `Course materials, software, and branding on ${brandDisplayName} are owned by ${legalEntityNameEn} or its licensors. You receive a limited license to access subscribed content while your subscription is active.`,
      ],
    },
    {
      heading: '8. Disclaimers and limitation of liability',
      paragraphs: [
        'The service and courses are provided "as is" to the extent permitted by law. We do not guarantee uninterrupted service or specific learning outcomes.',
        'To the extent permitted by law, our total liability relating to these Terms is limited to the subscription fees you paid in the twelve months before the claim.',
      ],
    },
    {
      heading: '9. Governing law',
      paragraphs: [
        `These Terms are governed by the laws of the ${governingLaw}. Disputes are subject to the courts of Jordan, subject to mandatory consumer protections.`,
      ],
    },
    {
      heading: '10. Contact',
      paragraphs: [`Questions about these Terms: ${supportEmail}.`],
    },
  ],
}
