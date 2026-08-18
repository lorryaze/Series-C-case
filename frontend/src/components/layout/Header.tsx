import { useAuth } from '../../context/AuthContext';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { humanize } from '../../utils/format';

export function Header({ title, subtitle }: { title: string; subtitle?: string }): JSX.Element {
  const { user, logout } = useAuth();

  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
        {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
      </div>
      {user && (
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-sm font-medium text-slate-800">{user.full_name}</p>
            <p className="text-xs text-slate-500">{user.email}</p>
          </div>
          <Badge tone={user.role === 'admin' ? 'info' : 'neutral'}>{humanize(user.role)}</Badge>
          <Button variant="secondary" size="sm" onClick={logout}>
            Log out
          </Button>
        </div>
      )}
    </header>
  );
}
