import { useEffect, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import Icon, { type IconName } from './Icon';
import { titleCase } from '../lib/format';

export function PageHeader({ title, right, pill }: { title: ReactNode; right?: ReactNode; pill?: ReactNode }) {
  return (
    <div className="ad-page-header">
      <div className="ad-page-title">
        <h2 className="ad-h2">
          {title}
          {pill}
        </h2>
        <a className="ad-docs-link" href="https://adapty.io/docs/ab-tests" target="_blank" rel="noreferrer">
          <Icon name="external" />
          Read the docs
        </a>
      </div>
      <div className="ad-header-actions">{right}</div>
    </div>
  );
}

export function Breadcrumb({ parent, parentHref, current, extra }: { parent?: string; parentHref: string; current: ReactNode; extra?: ReactNode }) {
  return (
    <div className="ad-breadcrumb">
      <Link className="ad-breadcrumb__back" to={parentHref} aria-label="Back">
        <Icon name="arrow-left" />
      </Link>
      {parent && (
        <>
          <Link className="ad-breadcrumb__parent" to={parentHref}>
            {parent}
          </Link>
          <span className="ad-breadcrumb__sep">/</span>
        </>
      )}
      <span className="ad-breadcrumb__current">{current}</span>
      {extra}
    </div>
  );
}

export function Skeleton({ width, height = 12, className = '', style }: { width?: number | string; height?: number; className?: string; style?: React.CSSProperties }) {
  return <div className={`ad-skeleton ${className}`} style={{ width, height, ...style }} />;
}

export function CardSkeleton() {
  return (
    <div className="ad-card" style={{ padding: 16 }}>
      <Skeleton width={320} height={20} className="rf-mb-8" />
      <Skeleton width={570} className="rf-mb-24" />
      {[1, 2, 3].map((i) => (
        <Skeleton key={i} style={{ margin: '20px 0' }} />
      ))}
    </div>
  );
}

export function EmptyState({ icon = 'ab', text, action, compact }: { icon?: IconName; text: ReactNode; action?: ReactNode; compact?: boolean }) {
  return (
    <div className={`ad-empty ${compact ? 'ad-empty--compact' : ''}`}>
      <span className="ad-empty__icon">
        <Icon name={icon} />
      </span>
      <p className="ad-empty__text">{text}</p>
      {action}
    </div>
  );
}

export function ErrorBox({ error }: { error: Error | null }) {
  if (!error) return null;
  return <div className="rf-error">Could not load: {error.message}</div>;
}

export function Pagination({ count }: { count: number }) {
  return (
    <div className="ad-pagination">
      <span className="ad-pagination__total">
        {count ? `1-${count} of ${count}` : '0 of 0'}
      </span>
      <button className="ad-pagination__item" disabled>
        <Icon name="chevron-left" size={16} />
      </button>
      <button className="ad-pagination__item is-active">1</button>
      <button className="ad-pagination__item" disabled>
        <Icon name="chevron-right" size={16} />
      </button>
    </div>
  );
}

export function StatusText({ state }: { state: string }) {
  return (
    <span className={`ad-status ad-status--${state}`}>
      {titleCase(state)}
      {state === 'live' && <span className="ad-live-dot" />}
    </span>
  );
}

export function Hint({ title, text, children, className = '', muted }: { title?: string; text: string; children: ReactNode; className?: string; muted?: boolean }) {
  return (
    <span className={`${muted ? 'ad-hint-muted' : 'ad-hint'} ${className}`} data-hint-title={title} data-hint={text}>
      {children}
    </span>
  );
}

export function SortTh({ label, right, help, sorted, className = '', style }: { label: string; right?: boolean; help?: string; sorted?: boolean; className?: string; style?: React.CSSProperties }) {
  const caret = (
    <span className="ad-sort">
      <span>▲</span>
      <span className={sorted ? 'is-active' : ''}>▼</span>
    </span>
  );
  return (
    <th className={`is-sortable ${right ? 'is-right' : ''} ${sorted ? 'is-sorted' : ''} ${className}`} style={style}>
      {right && caret}
      {help ? (
        <span className="ad-th-help" data-hint={help}>
          <Icon name="help" />
          {label}
        </span>
      ) : (
        label
      )}
      {!right && <> {caret}</>}
    </th>
  );
}

export function Modal({ open, onClose, title, info, footer, wide, children }: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  info?: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
  children?: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="ad-overlay is-open" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <section className={`ad-modal ${wide ? 'ad-modal--wide' : ''}`}>
        <button className="ad-modal__close" onClick={onClose} aria-label="Close">
          <Icon name="x" size={24} />
        </button>
        <h2 className="ad-modal__title">{title}</h2>
        {info && <div className="ad-modal__info">{info}</div>}
        <div className="ad-modal__content">{children}</div>
        {footer && <div className="ad-modal__footer">{footer}</div>}
      </section>
    </div>
  );
}

export function toast(message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') {
  if (typeof window.adToast === 'function') window.adToast(message, type);
}
