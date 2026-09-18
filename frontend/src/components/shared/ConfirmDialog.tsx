import { useEffect, useRef, useCallback } from 'react';
import { X } from 'lucide-react';

interface Props {
  open?: boolean;
  isOpen?: boolean;
  onClose?: () => void;
  onCancel?: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  confirmVariant?: 'danger' | 'primary';
  isDestructive?: boolean;
  isLoading?: boolean;
}

export function ConfirmDialog({
  open,
  isOpen,
  onClose,
  onCancel,
  onConfirm,
  title,
  message,
  confirmLabel = 'Confirm',
  confirmVariant = 'danger',
  isDestructive,
  isLoading = false,
}: Props) {
  const isDialogVisible = Boolean(open ?? isOpen);
  const handleClose = useCallback(() => {
    (onClose ?? onCancel)?.();
  }, [onClose, onCancel]);
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (isDialogVisible) confirmRef.current?.focus();
  }, [isDialogVisible]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isDialogVisible) handleClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [isDialogVisible, handleClose]);

  if (!isDialogVisible) return null;

  const isDanger = isDestructive !== undefined ? isDestructive : confirmVariant === 'danger';
  const confirmStyle = isDanger
    ? 'bg-rose-700 hover:bg-rose-600 text-white'
    : 'bg-cyan-700 hover:bg-cyan-600 text-white';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleClose}
        aria-hidden="true"
      />
      {/* Dialog */}
      <div className="relative z-10 w-full max-w-md mx-4 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-6">
        <button
          type="button"
          onClick={handleClose}
          className="absolute top-4 right-4 text-slate-500 hover:text-slate-300 transition-colors"
          aria-label="Close dialog"
        >
          <X className="w-4 h-4" />
        </button>
        <h2 id="confirm-title" className="text-slate-100 font-semibold text-lg mb-2">
          {title}
        </h2>
        <p className="text-slate-400 text-sm mb-6">{message}</p>
        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={handleClose}
            disabled={isLoading}
            className="px-4 py-2 rounded-lg text-sm text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            ref={confirmRef}
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 ${confirmStyle}`}
          >
            {isLoading ? 'Processing…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
