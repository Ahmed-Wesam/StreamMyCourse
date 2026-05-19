import { NavLink, Outlet } from 'react-router-dom'

const navItemClass = ({ isActive }: { isActive: boolean }) =>
  [
    'block rounded-xl px-4 py-2.5 text-sm transition-colors',
    isActive
      ? 'bg-blue-50 font-semibold text-blue-700'
      : 'font-medium text-muted-foreground hover:bg-muted/50 hover:text-foreground',
  ].join(' ')

export function AccountLayout() {
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-4 py-8 sm:px-6 lg:flex-row lg:px-8">
      <aside className="shrink-0 lg:w-56">
        <h1 className="text-2xl font-bold tracking-tight text-gray-900">Account</h1>
        <nav className="mt-6 flex flex-col gap-1" aria-label="Account">
          <NavLink to="/account/profile" className={navItemClass} end>
            Profile
          </NavLink>
          <NavLink to="/account/subscription" className={navItemClass}>
            Manage subscription
          </NavLink>
        </nav>
      </aside>
      <div className="min-w-0 flex-1">
        <Outlet />
      </div>
    </div>
  )
}
