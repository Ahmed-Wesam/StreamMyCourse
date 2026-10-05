import { ChevronDown } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { profileInitials } from '../../lib/profileInitials'

type ProfileMenuItem =
  | { href: string; label: string }
  | { label: string; onSelect: () => void }

type ProfileMenuProps = {
  name: string
  /** Used for avatar letters when pool/RDS names are missing (e.g. email → AH). */
  email?: string
  givenName?: string | null
  familyName?: string | null
  /** e.g. "Student" or "Instructor" */
  subtitle?: string
  items: ProfileMenuItem[]
  /** Student header uses the prototype dropdown. Omit for the teacher shell. */
  chrome?: 'prototype'
}

function prototypeFirstName(name: string): string {
  const first = name.trim().split(/\s+/)[0] || 'Student'
  return first.charAt(0).toUpperCase() + first.slice(1)
}

function isLinkItem(item: ProfileMenuItem): item is { href: string; label: string } {
  return 'href' in item
}

function cx(...parts: Array<string | undefined | false>) {
  return parts.filter(Boolean).join(' ')
}

export function ProfileMenu({ name, email, givenName, familyName, subtitle, items, chrome }: ProfileMenuProps) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const menuId = useId()
  const initials = profileInitials({ givenName, familyName, email, displayName: name })

  useEffect(() => {
    if (!open) return

    const onPointerDown = (event: MouseEvent) => {
      const root = rootRef.current
      if (!root) return
      if (event.target instanceof Node && root.contains(event.target)) return
      setOpen(false)
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      setOpen(false)
      if (chrome === 'prototype') rootRef.current?.focus()
      else triggerRef.current?.focus()
    }

    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [chrome, open])

  if (chrome === 'prototype') {
    return (
      <div
        ref={rootRef}
        id="navProfile"
        className={cx('nav-profile', open && 'is-open')}
        role="button"
        tabIndex={0}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        aria-label={name.trim() ? `Account menu for ${name.trim()}` : 'Account menu'}
        onClick={(event) => {
          const drop = event.currentTarget.querySelector('.nav-drop')
          if (drop && event.target instanceof Node && drop.contains(event.target)) return
          setOpen((value) => !value)
        }}
        onKeyDown={(event) => {
          if (event.target !== event.currentTarget) return
          if (event.key !== 'Enter' && event.key !== ' ') return
          event.preventDefault()
          setOpen((value) => !value)
        }}
      >
        <span className="nav-avatar" aria-hidden="true">
          {initials}
        </span>
        <svg
          className="nav-chev"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
        {open ? (
          <div id={menuId} role="menu" className="nav-drop">
            <div className="nav-drop-h">
              <span className="nav-avatar nav-avatar--menu" aria-hidden="true">
                {initials}
              </span>
              <div>
                <b>{prototypeFirstName(name)}</b>
                {subtitle ? <span className="nav-drop-role">{subtitle}</span> : null}
              </div>
            </div>
            {items.map((item) => {
              if (isLinkItem(item)) {
                const internal = item.href.startsWith('/')
                if (internal) {
                  return (
                    <Link
                      key={`link:${item.href}:${item.label}`}
                      role="menuitem"
                      to={item.href}
                      onClick={() => setOpen(false)}
                    >
                      {item.label}
                    </Link>
                  )
                }
                return (
                  <a
                    key={`a:${item.href}:${item.label}`}
                    role="menuitem"
                    href={item.href}
                    onClick={() => setOpen(false)}
                  >
                    {item.label}
                  </a>
                )
              }
              return (
                <button
                  key={`action:${item.label}`}
                  type="button"
                  role="menuitem"
                  className="logout"
                  onClick={() => {
                    setOpen(false)
                    item.onSelect()
                  }}
                >
                  {item.label}
                </button>
              )
            })}
          </div>
        ) : null}
      </div>
    )
  }

  return (
    <div ref={rootRef} className="relative inline-flex shrink-0">
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        aria-label={name.trim() ? `Account menu for ${name.trim()}` : 'Account menu'}
        onClick={() => setOpen((v) => !v)}
        className={cx(
          'inline-flex items-center gap-[7px] rounded-full border border-rs-line bg-white',
          'py-[5px] pl-[5px] pr-[11px] outline-none transition duration-200 ease-rs',
          'hover:border-[#d8e3fb] hover:bg-rs-sky-2',
          open && 'border-[#d8e3fb] bg-rs-sky-2',
        )}
      >
        <span
          aria-hidden="true"
          className="flex size-8 shrink-0 items-center justify-center rounded-full bg-rs-grad-cta text-[12px] font-extrabold tracking-[0.02em] text-white"
        >
          {initials}
        </span>
        <ChevronDown
          aria-hidden="true"
          className={cx(
            'size-3.5 text-rs-muted transition-transform duration-200 ease-rs',
            open && 'rotate-180 text-rs-navy',
          )}
        />
      </button>

      {open ? (
        <div
          id={menuId}
          role="menu"
          className="absolute right-0 top-[calc(100%+10px)] z-[60] min-w-[248px] rounded-2xl border border-rs-line bg-white p-2 shadow-rs-lg"
        >
          <div className="mb-1.5 flex items-center gap-3 border-b border-rs-line p-3">
            <span
              aria-hidden="true"
              className="flex size-9 shrink-0 items-center justify-center rounded-full bg-rs-grad-cta text-[13px] font-extrabold text-white"
            >
              {initials}
            </span>
            <div className="min-w-0">
              <b className="block text-sm font-extrabold tracking-[-0.01em] text-rs-ink">
                {name.trim() || 'Account'}
              </b>
              {subtitle ? (
                <span className="mt-px block text-xs font-semibold text-rs-muted">{subtitle}</span>
              ) : null}
            </div>
          </div>

          {items.map((item) => {
            const itemClass =
              'block w-full rounded-lg px-3 py-2.5 text-left text-sm font-semibold tracking-[-0.005em] text-rs-navy no-underline transition-colors hover:bg-rs-sky-2 hover:text-rs-blue'

            if (isLinkItem(item)) {
              const internal = item.href.startsWith('/')
              if (internal) {
                return (
                  <Link
                    key={`link:${item.href}:${item.label}`}
                    role="menuitem"
                    to={item.href}
                    className={itemClass}
                    onClick={() => setOpen(false)}
                  >
                    {item.label}
                  </Link>
                )
              }
              return (
                <a
                  key={`a:${item.href}:${item.label}`}
                  role="menuitem"
                  href={item.href}
                  className={itemClass}
                  onClick={() => setOpen(false)}
                >
                  {item.label}
                </a>
              )
            }

            return (
              <button
                key={`action:${item.label}`}
                type="button"
                role="menuitem"
                className={itemClass}
                onClick={() => {
                  setOpen(false)
                  item.onSelect()
                }}
              >
                {item.label}
              </button>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}
