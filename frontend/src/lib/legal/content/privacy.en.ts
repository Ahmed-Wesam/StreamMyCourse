import { legalConfig } from '../../legalConfig'
import type { LegalDocumentContent } from './types'

const {
  legalEntityNameEn,
  brandDisplayName,
  supportEmail,
  websiteHost,
  governingLaw,
} = legalConfig

export const privacyEn: LegalDocumentContent = {
  title: 'Privacy Policy',
  lastUpdated: '2026-05-23',
  sections: [
    {
      heading: '1. Introduction',
      paragraphs: [
        `${legalEntityNameEn} ("we", "us") operates ${brandDisplayName} at ${websiteHost}. This Privacy Policy explains what personal information we collect, how we use it, and your choices.`,
      ],
    },
    {
      heading: '2. Information we collect',
      paragraphs: [
        'Account information: name, email address, and identifiers from your Google sign-in.',
        'Subscription and billing information: subscription status, billing dates, and payment confirmation details from our payment provider (we do not receive or store your full card number).',
        'Usage information: course progress, quiz results, and how you use the service.',
        'Technical information: IP address, browser type, and device information collected in server logs for security and troubleshooting.',
        'Communications: information you send when you contact support.',
      ],
    },
    {
      heading: '3. How we use information',
      paragraphs: [
        'To provide the service, authenticate you, manage subscriptions, and give access to courses.',
        'To process payments, send service-related notices, and respond to support requests.',
        'To maintain security, prevent fraud, and improve the platform.',
        'We do not sell your personal information.',
      ],
    },
    {
      heading: '4. Sharing with service providers',
      paragraphs: [
        'We share information with companies that help us run the service, including:',
        'Google: sign-in authentication.',
        'Amazon Web Services: hosting, authentication, storage, and related cloud services.',
        'PayTabs: payment processing for subscriptions.',
        'These providers process data under their own privacy policies and only as needed to perform services for us. Some processing may occur outside Jordan.',
      ],
    },
    {
      heading: '5. Data retention',
      paragraphs: [
        'We keep account and subscription records while your account is active and for a reasonable period afterward for legal, accounting, and dispute purposes.',
        'You may request deletion subject to exceptions where we must retain data by law or for ongoing billing or disputes.',
      ],
    },
    {
      heading: '6. Your rights',
      paragraphs: [
        'Under applicable law in Jordan, including the Personal Data Protection Law where it applies, you may request access to, correction of, or deletion of your personal information.',
        `Contact us at ${supportEmail}. We may need to verify your identity before responding.`,
      ],
    },
    {
      heading: '7. Security',
      paragraphs: [
        'We use reasonable technical and organizational measures to protect personal information, including encryption in transit and access controls. No method of transmission or storage is completely secure.',
      ],
    },
    {
      heading: '8. Cookies and similar technologies',
      paragraphs: [
        'We use cookies and local storage to keep you signed in and to operate the site. You can control cookies through your browser settings, but some features may not work if you disable them.',
      ],
    },
    {
      heading: '9. Children',
      paragraphs: [
        `${brandDisplayName} is not directed to children under 13. We do not knowingly collect personal information from children under 13.`,
      ],
    },
    {
      heading: '10. Changes to this policy',
      paragraphs: [
        'We may update this Privacy Policy from time to time. We will post the revised policy on this page and update the "Last updated" date. Material changes may also be communicated on the site or by email.',
      ],
    },
    {
      heading: '11. Contact us',
      paragraphs: [
        `Questions or privacy requests: ${supportEmail}.`,
        `Governing law: ${governingLaw}.`,
      ],
    },
  ],
}
