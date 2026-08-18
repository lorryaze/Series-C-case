import { NavLink } from 'react-router-dom';

interface NavItem {
  to: string;
  label: string;
  description: string;
  icon: string;
}

const NAV_ITEMS: NavItem[] = [
  { to: '/kyc', label: 'KYC Review Queue', description: 'Compliance onboarding', icon: '🛡' },
  { to: '/refunds', label: 'Refunds', description: 'Disputes & payouts', icon: '💸' },
  { to: '/feature-flags', label: 'Feature Flags', description: 'Release control', icon: '🚦' },
];

export function Sidebar(): JSX.Element {
  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-slate-800 bg-slate-900 text-slate-300">
      <div className="border-b border-slate-800 px-5 py-4">
        <p className="text-sm font-semibold text-white">Internal Tools</p>
        <p className="text-xs text-slate-400">Shared platform</p>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              [
                'block rounded-md px-3 py-2 transition',
                isActive ? 'bg-brand-600 text-white' : 'hover:bg-slate-800 hover:text-white',
              ].join(' ')
            }
          >
            <span className="flex items-center gap-2 text-sm font-medium">
              <span aria-hidden>{item.icon}</span>
              {item.label}
            </span>
            <span className="ml-6 block text-xs text-slate-400">{item.description}</span>
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-slate-800 px-5 py-3 text-xs text-slate-500">
        <a
          href={import.meta.env.VITE_API_DOCS_URL ?? 'http://localhost:8000/docs'}
          className="hover:text-slate-300"
          target="_blank"
          rel="noreferrer"
        >
          API documentation ↗
        </a>
      </div>
    </aside>
  );
}
