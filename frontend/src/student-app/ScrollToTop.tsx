import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

export function ScrollToTop() {
  const location = useLocation()

  useEffect(() => {
    // Allow the next paint so the element exists before we scroll to it.
    requestAnimationFrame(() => {
      if (location.hash) {
        const id = location.hash.replace('#', '')
        const el = document.getElementById(id)
        if (el) {
          el.scrollIntoView({ block: 'start' })
          return
        }
      }
      window.scrollTo({ top: 0, left: 0, behavior: 'auto' })
    })
  }, [location.pathname, location.hash])

  return null
}

