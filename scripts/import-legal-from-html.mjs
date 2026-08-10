/**
 * One-shot helper: extract legal policy prose from data/ALL PAGES/*.html
 * into frontend/src/lib/legal/content/*.en.ts modules.
 *
 * Usage (repo root): node scripts/import-legal-from-html.mjs
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, '..')
const htmlDir = path.join(repoRoot, 'data', 'ALL PAGES')
const outDir = path.join(repoRoot, 'frontend', 'src', 'lib', 'legal', 'content')

const DOCS = [
  {
    html: 'PrivacyPolicy.html',
    exportName: 'privacyEn',
    outFile: 'privacy.en.ts',
    title: 'Privacy Policy',
    lastUpdated: '2026-06-01',
  },
  {
    html: 'TermsOfService.html',
    exportName: 'termsEn',
    outFile: 'terms.en.ts',
    title: 'Terms & Conditions',
    lastUpdated: '2026-06-01',
  },
  {
    html: 'RefundPolicy.html',
    exportName: 'refundEn',
    outFile: 'refund.en.ts',
    title: 'Refund & Cancellation Policy',
    lastUpdated: '2026-06-01',
  },
  {
    html: 'DeliveryPolicy.html',
    exportName: 'deliveryEn',
    outFile: 'delivery.en.ts',
    title: 'Delivery Policy',
    lastUpdated: '2026-06-01',
  },
  {
    html: 'EducationalDisclaimer.html',
    exportName: 'educationalDisclaimerEn',
    outFile: 'educational-disclaimer.en.ts',
    title: 'Educational Disclaimer',
    lastUpdated: '2026-06-01',
  },
]

function decodeHtml(text) {
  return text
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, ' ')
    .trim()
}

function stripTags(html) {
  return decodeHtml(html.replace(/<[^>]+>/g, ' '))
}

function extractContactEmail(bodyHtml) {
  const match = bodyHtml.match(/mailto:([^"']+)/)
  return match ? match[1] : null
}

function bodyToParagraphs(bodyHtml) {
  const chunks = bodyHtml
    .replace(/<div class="ps-contact-card"[\s\S]*?<\/div>\s*<\/div>\s*<\/div>/gi, (block) => {
      const email = extractContactEmail(block)
      return email ? `<p>Contact: ${email}</p>` : ''
    })
    .split(/(?=<h4>|<p>|<ul>)/gi)
    .map((chunk) => chunk.trim())
    .filter(Boolean)

  const paragraphs = []

  for (const chunk of chunks) {
    if (chunk.startsWith('<h4>')) {
      const heading = stripTags(chunk.match(/<h4>([\s\S]*?)<\/h4>/)?.[1] ?? '')
      if (heading) paragraphs.push(heading)
      continue
    }
    if (chunk.startsWith('<p>')) {
      const matches = [...chunk.matchAll(/<p>([\s\S]*?)<\/p>/gi)]
      for (const m of matches) {
        const text = stripTags(m[1])
        if (text) paragraphs.push(text)
      }
      continue
    }
    if (chunk.includes('<ul>')) {
      const items = [...chunk.matchAll(/<li>([\s\S]*?)<\/li>/gi)].map((m) => stripTags(m[1]))
      for (const item of items) {
        if (item) paragraphs.push(`• ${item}`)
      }
    }
  }

  return paragraphs.filter(Boolean)
}

function extractSections(html) {
  const sections = []

  const introMatch = html.match(
    /<div class="policy-intro-section"[\s\S]*?<div class="ps-body">([\s\S]*?)<\/div>(?:\s*<div class="pi-operator">([\s\S]*?)<\/div>)?/i,
  )
  if (introMatch) {
    const introParagraphs = bodyToParagraphs(introMatch[1])
    if (introMatch[2]) {
      const operator = stripTags(introMatch[2].replace(/<\/?b>/gi, ''))
      if (operator) introParagraphs.push(operator)
    }
    if (introParagraphs.length) {
      sections.push({ heading: 'Introduction', paragraphs: introParagraphs })
    }
  }

  const sectionRegex =
    /<div class="policy-section"[^>]*>[\s\S]*?<div class="ps-title">([\s\S]*?)<\/div>[\s\S]*?<div class="ps-body">([\s\S]*?)<\/div>\s*<\/div>/gi

  let match
  while ((match = sectionRegex.exec(html)) !== null) {
    const heading = decodeHtml(match[1].replace(/<[^>]+>/g, ''))
    const paragraphs = bodyToParagraphs(match[2])
    if (heading && paragraphs.length) {
      sections.push({ heading, paragraphs })
    }
  }

  return sections
}

function escapeString(value) {
  return value.replace(/\\/g, '\\\\').replace(/'/g, "\\'")
}

function emitTs({ exportName, title, lastUpdated, sections }) {
  const lines = [
    "import { legalConfig } from '../../legalConfig'",
    "import type { LegalDocumentContent } from './types'",
    '',
    'const { supportEmail } = legalConfig',
    '',
    `export const ${exportName}: LegalDocumentContent = {`,
    `  title: '${escapeString(title)}',`,
    `  lastUpdated: '${lastUpdated}',`,
    '  sections: [',
  ]

  for (const section of sections) {
    const paragraphs = [...section.paragraphs]
    if (section.heading === 'Contact' && !paragraphs.some((p) => p.includes('supportEmail'))) {
      paragraphs.push('__CONTACT_EMAIL__')
    }
    lines.push('    {')
    lines.push(`      heading: '${escapeString(section.heading)}',`)
    lines.push('      paragraphs: [')
    for (const paragraph of paragraphs) {
      if (paragraph === '__CONTACT_EMAIL__') {
        lines.push("        'For inquiries: ' + supportEmail,")
        continue
      }
      lines.push(`        '${escapeString(paragraph.replace(/\$\{/g, '\\${'))}',`)
    }
    lines.push('      ],')
    lines.push('    },')
  }

  lines.push('  ],', '}', '')
  return lines.join('\n')
}

for (const doc of DOCS) {
  const htmlPath = path.join(htmlDir, doc.html)
  const html = fs.readFileSync(htmlPath, 'utf8')
  const sections = extractSections(html)

  if (!sections.length) {
    console.error(`No sections extracted from ${doc.html}`)
    process.exitCode = 1
    continue
  }

  const ts = emitTs({ ...doc, sections })

  const outPath = path.join(outDir, doc.outFile)
  fs.writeFileSync(outPath, ts, 'utf8')
  console.log(`Wrote ${path.relative(repoRoot, outPath)} (${sections.length} sections)`)
}
