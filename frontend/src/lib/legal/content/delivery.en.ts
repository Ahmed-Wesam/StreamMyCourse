import { legalConfig } from '../../legalConfig'
import type { LegalDocumentContent } from './types'

const { supportEmail } = legalConfig

export const deliveryEn: LegalDocumentContent = {
  title: 'Delivery Policy',
  lastUpdated: '2026-06-01',
  sections: [
    {
      heading: 'Introduction',
      paragraphs: [
        'Research Spectrum provides digital educational content and services through an online learning platform.',
        'This Delivery Policy explains how access to purchased products and services is delivered to users.',
      ],
    },
    {
      heading: 'Nature of Products',
      paragraphs: [
        'Research Spectrum currently offers the following digital products:',
        '• Online courses',
        '• Course bundles',
        '• Educational resources',
        '• Assessments',
        '• Certifications',
        'No physical products are shipped or delivered.',
      ],
    },
    {
      heading: 'Delivery Method',
      paragraphs: [
        'All products and services are delivered electronically through the Research Spectrum platform.',
        'Upon successful payment, eligible users will receive access to purchased content through their Research Spectrum account.',
        'Delivery occurs through:',
        '• Website access',
        '• User dashboard access',
        '• Online learning platform access',
        '• Electronic communications where applicable',
      ],
    },
    {
      heading: 'Delivery Timeframe',
      paragraphs: [
        'Access to purchased courses and digital content is typically granted automatically and immediately following successful payment confirmation.',
        'In rare circumstances involving:',
        '• Payment verification',
        '• Technical issues',
        '• System maintenance',
        '• Security reviews',
        '• Third-party service interruptions',
        'delivery may be delayed.',
        'Research Spectrum will make reasonable efforts to resolve such issues promptly.',
      ],
    },
    {
      heading: 'Technical Access Issues',
      paragraphs: [
        'If payment is successfully completed but access to purchased content is not granted, users should contact:',
      ],
    },
    {
      heading: 'User Responsibilities',
      paragraphs: [
        'Users are responsible for:',
        '• Providing accurate account information',
        '• Maintaining access to their registered email address',
        '• Maintaining internet connectivity',
        '• Using compatible devices and software',
        '• Protecting account credentials',
        'Research Spectrum is not responsible for access issues resulting from:',
        '• Incorrect account information',
        '• User device problems',
        '• Internet connectivity issues',
        '• Third-party software conflicts',
        '• Unauthorized account sharing',
      ],
    },
    {
      heading: 'Device Restrictions',
      paragraphs: [
        'Access to purchased content is subject to platform licensing restrictions, including:',
        '• Maximum of three (3) registered devices per account',
        '• One (1) active session at a time',
        '• Technical measures used to protect intellectual property',
        'These restrictions form part of the delivery and access model of Research Spectrum Services.',
      ],
    },
    {
      heading: 'Availability of Content',
      paragraphs: [
        'Access to purchased courses remains available for as long as Research Spectrum continues to operate the applicable course and platform, subject to the Terms & Conditions. Course access is licensed, not sold, and is not guaranteed in perpetuity independent of platform operation.',
        'Research Spectrum reserves the right to:',
        '• Modify courses',
        '• Update content',
        '• Reorganize modules',
        '• Add or remove educational materials',
        '• Improve course structures',
        '• Retire unsupported courses',
        'at its sole discretion.',
      ],
    },
    {
      heading: 'International Delivery',
      paragraphs: [
        'Because Research Spectrum delivers content electronically, Services may generally be accessed internationally where legally permitted.',
        'Users are responsible for complying with local laws and regulations applicable in their jurisdiction.',
      ],
    },
    {
      heading: 'Future Services',
      paragraphs: [
        'Research Spectrum may introduce additional services in the future. These may include, but are not limited to:',
        '• Live workshops',
        '• Mentorship sessions',
        '• Consultations',
        '• Interactive educational events',
        'None of the above are currently available. Where such services are introduced, their specific delivery methods, access requirements, and terms will be communicated on the applicable product page at the time of launch.',
      ],
    },
    {
      heading: 'Force Majeure',
      paragraphs: [
        'Research Spectrum shall not be responsible for delays or interruptions in delivery caused by events beyond its reasonable control, including:',
        '• Internet outages',
        '• Cybersecurity incidents',
        '• Government restrictions',
        '• Natural disasters',
        '• Infrastructure failures',
        '• Third-party service outages',
      ],
    },
    {
      heading: 'Policy Changes',
      paragraphs: [
        'Research Spectrum reserves the right to modify this Delivery Policy at any time.',
        'Updated versions will be published on the website.',
        'Continued use of the Services following publication of updated policies constitutes acceptance of the revised policy.',
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
        'For questions regarding this Delivery Policy, please contact:',
        'For inquiries: ' + supportEmail,
      ],
    },
  ],
}
