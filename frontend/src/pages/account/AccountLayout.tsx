import { NavLink, Outlet } from 'react-router-dom'

const navItemClass = ({ isActive }: { isActive: boolean }) =>
  [
    'block rounded-xl px-4 py-2.5 text-sm transition-colors',
    isActive
      ? 'bg-rs-sky-2 font-bold text-rs-blue'
      : 'font-semibold text-rs-muted hover:bg-rs-sky-2/60 hover:text-rs-navy',
  ].join(' ')

export function AccountLayout() {
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-4 py-8 text-rs-ink sm:px-6 lg:flex-row lg:px-8">
      <aside className="shrink-0 lg:w-56">
        <h1 className="text-2xl font-extrabold tracking-tight text-rs-ink">Account</h1>
        <nav className="mt-6 flex flex-col gap-1" aria-label="Account">
          <NavLink to="/account/profile" className={navItemClass} end>
            Profile
          </NavLink>
          <NavLink to="/account/purchases" className={navItemClass}>
            My purchases
          </NavLink>
        </nav>
      </aside>
      <div className="min-w-0 flex-1">
        <Outlet />
      </div>
    </div>
  )
}
