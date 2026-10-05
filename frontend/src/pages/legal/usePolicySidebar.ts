import { useEffect, type RefObject } from 'react'

/** Click-to-section and scroll spy from the prototype legal pages. */
export function usePolicySidebar(rootRef: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const current = rootRef.current
    if (!current) return
    const root: HTMLElement = current

    const links = Array.from(root.querySelectorAll<HTMLButtonElement>('.sidebar-link'))
    const sections = links.flatMap((link) => {
      const id = link.getAttribute('data-target')
      if (!id || !/^[A-Za-z][\w-]*$/.test(id)) return []
      const section = root.querySelector<HTMLElement>(`#${id}`)
      return section ? [section] : []
    })

    function onClick(event: Event) {
      const link = event.currentTarget
      if (!(link instanceof HTMLButtonElement)) return
      for (const item of links) item.classList.remove('active')
      link.classList.add('active')
      const id = link.getAttribute('data-target')
      const target = id && /^[A-Za-z][\w-]*$/.test(id) ? root.querySelector<HTMLElement>(`#${id}`) : null
      if (!target) return
      const offset = target.getBoundingClientRect().top + window.scrollY - 110
      window.scrollTo({ top: offset, behavior: 'smooth' })
    }

    for (const link of links) link.addEventListener('click', onClick)

    let frame = 0
    function updateActive() {
      if (frame) return
      frame = window.requestAnimationFrame(() => {
        frame = 0
        const scrollY = window.scrollY + 130
        let activeId: string | null = null
        for (const section of sections) {
          if (section.getBoundingClientRect().top + window.scrollY <= scrollY) activeId = section.id
        }
        for (const link of links) {
          link.classList.toggle('active', link.getAttribute('data-target') === activeId)
        }
      })
    }

    window.addEventListener('scroll', updateActive, { passive: true })
    updateActive()

    return () => {
      for (const link of links) link.removeEventListener('click', onClick)
      window.removeEventListener('scroll', updateActive)
      if (frame) window.cancelAnimationFrame(frame)
    }
  }, [rootRef])
}
