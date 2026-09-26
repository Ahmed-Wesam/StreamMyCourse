import { Check, Copy, Mail } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Eyebrow } from '../components/ui/Eyebrow'
import { Field } from '../components/ui/Field'
import { SectionHeader } from '../components/ui/SectionHeader'
import { legalConfig } from '../lib/legalConfig'
import {
  contactCategories,
  contactChannels,
  contactFormCopy,
  contactHero,
} from '../lib/marketing/contactCopy'
import { usePageTitle } from '../lib/page-title'

export default function ContactPage() {
  usePageTitle('Contact')

  const [status, setStatus] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  async function handleCopyEmail() {
    try {
      await navigator.clipboard.writeText(legalConfig.supportEmail)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setStatus(contactFormCopy.unavailableStatus)
  }

  return (
    <div className="min-h-screen bg-white text-rs-ink" data-testid="student-page-contact">
      <section className="relative overflow-hidden bg-gradient-to-b from-rs-sky-2 to-white px-5 pb-[76px] pt-16 sm:px-7">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(720px_480px_at_85%_10%,rgba(58,134,255,.12),transparent_62%),radial-gradient(500px_360px_at_0%_40%,rgba(30,94,255,.06),transparent_60%)]"
        />
        <div className="relative mx-auto grid max-w-wrap items-start gap-[60px] nav:grid-cols-[1.15fr_.85fr]">
          <div>
            <Eyebrow>{contactHero.eyebrow}</Eyebrow>
            <h1 className="mt-[18px] text-[clamp(36px,5vw,58px)] font-extrabold leading-[1.05] tracking-tight text-rs-ink">
              {contactHero.titleLine1}
              <br />
              <span className="bg-rs-grad-cta bg-clip-text text-transparent">
                {contactHero.titleHighlight}
              </span>
            </h1>
            <p className="mt-4 max-w-[480px] text-[17px] leading-relaxed text-rs-body">
              {contactHero.sub}
            </p>
            <ul className="mt-[26px] mb-7 flex list-none flex-col gap-2.5 p-0">
              {contactHero.trustItems.map((item) => (
                <li
                  key={item}
                  className="flex items-center gap-[11px] text-[15px] font-bold text-rs-navy"
                >
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-[7px] bg-rs-grad-cta text-white shadow-[0_6px_14px_-6px_rgba(30,94,255,.55)]">
                    <Check aria-hidden className="size-[13px]" strokeWidth={2.8} />
                  </span>
                  {item}
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-3">
              <Button href="#contact-form" arrow>
                {contactHero.primaryCta}
              </Button>
              <Button to="/faq" variant="ghost">
                {contactHero.secondaryCta}
              </Button>
            </div>
          </div>

          <Card className="rounded-[22px] p-[26px] shadow-rs-lg">
            <p className="mb-4 text-[13px] font-extrabold uppercase tracking-[0.08em] text-rs-muted">
              {contactHero.overview.title}
            </p>
            <dl className="m-0">
              {contactHero.overview.rows.map((row) => (
                <div
                  key={row.label}
                  className="flex flex-wrap items-start justify-between gap-2.5 border-b border-rs-line-2 py-3 first:pt-0 last:border-b-0 last:pb-0"
                >
                  <dt className="whitespace-nowrap text-[12.5px] font-bold text-rs-muted">
                    {row.label}
                  </dt>
                  <dd className="m-0 max-w-[180px] text-right text-[13.5px] font-extrabold text-rs-ink">
                    {row.value}
                  </dd>
                </div>
              ))}
            </dl>
          </Card>
        </div>
      </section>

      <section className="px-5 py-14 sm:px-7">
        <div className="mx-auto max-w-wrap">
          <div className="mb-8">
            <SectionHeader
              kicker={contactChannels.kicker}
              title={contactChannels.title}
              lead={contactChannels.lead}
            />
          </div>
          <Card className="mx-auto max-w-md rounded-[18px] p-[22px_20px] shadow-rs-sm">
            <div className="mb-3 flex size-10 items-center justify-center rounded-[11px] border border-[#e2ebff] bg-rs-grad-soft text-rs-blue">
              <Mail aria-hidden className="size-[18px]" strokeWidth={2} />
            </div>
            <p className="mb-1 text-[11.5px] font-extrabold uppercase tracking-[0.08em] text-rs-muted">
              {contactChannels.email.label}
            </p>
            <p className="break-all text-[13px] font-extrabold tracking-tight text-rs-ink">
              {legalConfig.supportEmail}
            </p>
            <p className="mb-3.5 mt-1 text-[12.5px] font-semibold text-rs-muted">
              {contactChannels.email.sub}
            </p>
            <div className="flex flex-wrap gap-2.5">
              <a
                href={`mailto:${legalConfig.supportEmail}`}
                className="inline-flex items-center gap-1.5 rounded-full border-[1.5px] border-rs-line-2 bg-rs-sky-2 px-4 py-2 text-[13px] font-bold text-rs-blue no-underline transition hover:border-rs-blue hover:bg-rs-sky"
              >
                <Mail aria-hidden className="size-[13px]" strokeWidth={2} />
                {contactChannels.email.mailtoLabel}
              </a>
              <button
                type="button"
                onClick={() => {
                  void handleCopyEmail()
                }}
                className="inline-flex items-center gap-1.5 rounded-full border-[1.5px] border-rs-line-2 bg-rs-sky-2 px-4 py-2 text-[13px] font-bold text-rs-blue transition hover:border-rs-blue hover:bg-rs-sky"
              >
                <Copy aria-hidden className="size-[13px]" strokeWidth={2} />
                {copied ? 'Copied' : contactChannels.email.copyLabel}
              </button>
            </div>
          </Card>
        </div>
      </section>

      <section
        id="contact-form"
        className="border-y border-rs-line-2 bg-rs-sky-2 px-5 py-20 sm:px-7"
      >
        <div className="mx-auto max-w-wrap">
          <div className="mb-9">
            <SectionHeader
              kicker={contactFormCopy.kicker}
              title={contactFormCopy.title}
              lead={contactFormCopy.lead}
            />
          </div>
          <Card className="mx-auto max-w-[820px] rounded-[24px] p-6 shadow-rs-sm sm:p-9">
            <h3 className="mb-1 flex items-center gap-[11px] text-xl font-extrabold tracking-tight text-rs-ink">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-[10px] border border-[#e2ebff] bg-rs-grad-soft text-rs-blue">
                <Mail aria-hidden className="size-[17px]" strokeWidth={2} />
              </span>
              {contactFormCopy.formTitle}
            </h3>
            <p className="mb-6 text-sm font-semibold text-rs-muted">{contactFormCopy.formSub}</p>

            <form onSubmit={handleSubmit} noValidate autoComplete="on">
              <div className="grid gap-3.5 sm:grid-cols-2">
                <Field label={contactFormCopy.nameLabel}>
                  <input
                    type="text"
                    name="name"
                    placeholder={contactFormCopy.namePlaceholder}
                    autoComplete="name"
                    aria-required="true"
                  />
                </Field>
                <Field label={contactFormCopy.emailLabel}>
                  <input
                    type="email"
                    name="email"
                    placeholder={contactFormCopy.emailPlaceholder}
                    autoComplete="email"
                    inputMode="email"
                    aria-required="true"
                  />
                </Field>
              </div>
              <div className="grid gap-3.5 sm:grid-cols-2">
                <Field label={contactFormCopy.categoryLabel}>
                  <select name="category" aria-required="true" defaultValue="">
                    <option value="">{contactFormCopy.categoryPlaceholder}</option>
                    {contactCategories.map((category) => (
                      <option key={category} value={category}>
                        {category}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label={contactFormCopy.subjectLabel}>
                  <input
                    type="text"
                    name="subject"
                    placeholder={contactFormCopy.subjectPlaceholder}
                    aria-required="true"
                  />
                </Field>
              </div>
              <Field label={contactFormCopy.messageLabel}>
                <textarea
                  name="message"
                  rows={5}
                  placeholder={contactFormCopy.messagePlaceholder}
                  aria-required="true"
                  className="min-h-[120px] resize-y"
                />
              </Field>
              <Field label={contactFormCopy.attachmentLabel} hint={contactFormCopy.attachmentHint}>
                <input
                  type="file"
                  name="attachment"
                  disabled
                  accept=".pdf,.docx,.doc,.png,.jpg,.jpeg,.zip"
                  aria-label="Choose file"
                />
              </Field>

              {status ? (
                <p
                  role="status"
                  className="mb-4 rounded-[10px] border border-rs-line bg-rs-sky-2 px-3.5 py-2.5 text-[13.5px] font-bold text-rs-navy"
                >
                  {status}
                </p>
              ) : null}

              <div className="flex flex-wrap items-center gap-3">
                <Button type="submit" arrow>
                  {contactFormCopy.submitLabel}
                </Button>
                <span className="text-[13px] font-semibold text-rs-muted">
                  {contactFormCopy.responseNote}
                </span>
              </div>
            </form>

            <p className="mt-6 text-[13px] font-semibold text-rs-muted">
              Prefer email?{' '}
              <a
                href={`mailto:${legalConfig.supportEmail}`}
                className="font-bold text-rs-blue no-underline hover:underline"
              >
                {legalConfig.supportEmail}
              </a>
            </p>
          </Card>
        </div>
      </section>

      <section className="px-5 py-16 text-center sm:px-7">
        <p className="text-[15px] text-rs-body">
          Looking for quick answers?{' '}
          <Link to="/faq" className="font-bold text-rs-blue no-underline hover:underline">
            Browse the FAQ
          </Link>
          .
        </p>
      </section>
    </div>
  )
}
