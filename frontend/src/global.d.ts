// Globals installed by the Adapty style kit scripts (public/kit/js).
declare function adToast(message: string, type?: 'success' | 'error' | 'info' | 'warning', ms?: number): void;
declare function adIcon(name: string, className?: string): string;
declare const adModal: { open(id: string): void; close(id?: string): void };

interface Window {
  adToast: typeof adToast;
  adIcon: typeof adIcon;
  adModal: typeof adModal;
}
