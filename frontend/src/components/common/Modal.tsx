import type { ReactNode } from 'react';
import { useEffect } from 'react';

interface ModalProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  width?: 'md' | 'lg' | 'xl';
}

const WIDTHS = { md: 'max-w-md', lg: 'max-w-2xl', xl: 'max-w-4xl' } as const;

export function Modal({
  open,
  title,
  onClose,
  children,
  footer,
  width = 'lg',
}: ModalProps): JSX.Element | null {
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4 sm:p-8">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`w-full ${WIDTHS[width]} rounded-lg bg-white shadow-xl`}
      >
        <header className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <h2 className="text-base font-semibold text-slate-800">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            ✕
          </button>
        </header>
        <div className="px-5 py-4">{children}</div>
        {footer && (
          <footer className="flex justify-end gap-2 border-t border-slate-200 bg-slate-50 px-5 py-3">
            {footer}
          </footer>
        )}
      </div>
    </div>
  );
}
