import { Link } from 'react-router-dom'

export function Footer() {
  return (
    <footer className="border-t border-slate-200/80 bg-slate-100/85 backdrop-blur-[2px]">
      <div className="mx-auto max-w-7xl px-3 py-10 sm:px-5 lg:px-10">
        <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
          <Link to="/" className="text-sm font-semibold text-gray-900">
            StreamMyCourse
          </Link>
          <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-gray-600">
            <a href="/#contact" className="hover:text-gray-900">
              Privacy
            </a>
            <a href="/#contact" className="hover:text-gray-900">
              Terms &amp; Conditions
            </a>
          </div>
        </div>
        <p className="mt-6 text-center text-xs text-gray-500">
          © {new Date().getFullYear()} StreamMyCourse. All rights reserved.
        </p>
      </div>
    </footer>
  )
}
