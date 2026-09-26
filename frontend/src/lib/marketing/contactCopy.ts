/** Static Contact marketing copy (no JSX). Prototype text for RS-2 Slice D4. */

export const contactCategories = [
  'General Question',
  'Course Support',
  'Assignment Support',
  'Certificate Support',
  'Research Team',
  'Technical Issue',
  'Billing Question',
  'Partnership Inquiry',
] as const

export const contactHero = {
  eyebrow: 'Contact Research Spectrum',
  titleLine1: 'How Can We',
  titleHighlight: 'Help You?',
  sub: "Whether you have questions about courses, certificates, assignments, technical issues, or the Research Team, we're here to help every step of the way.",
  trustItems: [
    'Student Support',
    'Technical Assistance',
    'Certificate Support',
    'Research Team Questions',
  ] as const,
  primaryCta: 'Send Message',
  secondaryCta: 'Browse FAQ',
  overview: {
    title: 'Support Overview',
    rows: [
      { label: 'Response Time', value: '1–2 Business Days' },
      { label: 'Languages', value: 'Arabic & English' },
      { label: 'Support Channels', value: 'Email · Contact Form · Instagram' },
      { label: 'Availability', value: 'Worldwide Online Support' },
    ] as const,
  },
} as const

export const contactChannels = {
  kicker: 'Reach Us',
  title: 'Official Communication Channels',
  lead: 'Research Spectrum is accessible through multiple channels. Use whichever method works best for you.',
  email: {
    label: 'Email Support',
    sub: 'Primary support channel for all enquiries.',
    copyLabel: 'Copy Email',
    mailtoLabel: 'Email support',
  },
} as const

export const contactFormCopy = {
  kicker: 'Get In Touch',
  title: 'Send Us a Message',
  lead: 'Fill out the form below and a member of the Research Spectrum support team will respond within 1–2 business days.',
  formTitle: 'Contact Form',
  formSub: 'All fields marked as required must be completed. We will respond to your email address.',
  nameLabel: 'Full Name',
  namePlaceholder: 'Your full name',
  emailLabel: 'Email Address',
  emailPlaceholder: 'your@email.com',
  categoryLabel: 'Subject Category',
  categoryPlaceholder: 'Select a category…',
  subjectLabel: 'Subject',
  subjectPlaceholder: 'Brief description of your question',
  messageLabel: 'Message',
  messagePlaceholder:
    'Describe your question or issue in detail. The more information you provide, the faster we can help.',
  attachmentLabel: 'Attachment (optional)',
  attachmentHint: 'File uploads are not available yet.',
  submitLabel: 'Send Message',
  responseNote: 'We respond within 1–2 business days',
  unavailableStatus:
    'Messaging is not available yet. Please email support using the address above.',
} as const
