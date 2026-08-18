import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';

/** Shell every tool renders inside: sidebar navigation plus the page outlet. */
export function AppShell(): JSX.Element {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-x-hidden">
        <Outlet />
      </main>
    </div>
  );
}
