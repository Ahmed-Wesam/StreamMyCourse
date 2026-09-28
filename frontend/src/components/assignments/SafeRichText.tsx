import { createElement, type ReactNode } from 'react'

const ALLOWED_TAGS = new Set(['p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'a'])

function isHttpsHref(href: string): boolean {
  try {
    const u = new URL(href)
    return u.protocol === 'https:'
  } catch {
    return false
  }
}

function hasDangerousAttr(el: Element): boolean {
  for (const attr of Array.from(el.attributes)) {
    const name = attr.name.toLowerCase()
    if (name.startsWith('on')) return true
    if (name === 'srcdoc') return true
  }
  return false
}

function renderNode(node: Node, key: string): ReactNode {
  if (node.nodeType === Node.TEXT_NODE) {
    return node.textContent
  }
  if (node.nodeType !== Node.ELEMENT_NODE) {
    return null
  }
  const el = node as Element
  const tag = el.tagName.toLowerCase()

  if (tag === 'script' || tag === 'style' || tag === 'iframe' || tag === 'object' || tag === 'embed') {
    return null
  }

  if (!ALLOWED_TAGS.has(tag) || hasDangerousAttr(el)) {
    return Array.from(el.childNodes).map((child, i) => renderNode(child, `${key}-${i}`))
  }

  const children = Array.from(el.childNodes).map((child, i) => renderNode(child, `${key}-${i}`))

  if (tag === 'br') {
    return createElement('br', { key })
  }

  if (tag === 'a') {
    const href = el.getAttribute('href')?.trim() ?? ''
    if (!isHttpsHref(href)) {
      return children
    }
    return createElement(
      'a',
      { key, href, rel: 'noopener noreferrer', target: '_blank' },
      ...children,
    )
  }

  return createElement(tag, { key }, ...children)
}

/**
 * Renders a narrow allowlist of HTML tags without using dangerouslySetInnerHTML.
 * Disallowed tags (including script) are dropped; their text children may still appear.
 */
export function SafeRichText({ html, className }: { html: string; className?: string }) {
  if (typeof DOMParser === 'undefined') {
    return createElement('div', { className }, html.replace(/<[^>]*>/g, ''))
  }

  const doc = new DOMParser().parseFromString(html, 'text/html')
  const body = doc.body
  const nodes = Array.from(body.childNodes).map((child, i) => renderNode(child, `n${i}`))

  return createElement('div', { className, 'data-testid': 'safe-rich-text' }, ...nodes)
}
