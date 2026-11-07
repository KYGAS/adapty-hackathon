// Icons come from the kit's sprite (public/kit/js/adapty-icons.js): 20px outline glyphs referenced by id.
export type IconName =
  | 'overview' | 'analytics' | 'users' | 'box' | 'flows' | 'pin' | 'message' | 'ab' | 'rocket' | 'refund' | 'dollar' | 'plug'
  | 'bell' | 'chevron-down' | 'chevron-up' | 'chevron-right' | 'chevron-left' | 'chevrons-left' | 'arrow-left' | 'external'
  | 'search' | 'x' | 'check' | 'check-circle' | 'more' | 'metrics' | 'trend' | 'stop' | 'play' | 'pencil' | 'copy' | 'branch'
  | 'archive' | 'trash' | 'plus' | 'calendar' | 'download' | 'file' | 'sliders' | 'user-plus' | 'hash' | 'sync' | 'clock'
  | 'image' | 'info' | 'warning' | 'help' | 'sparkle' | 'upload' | 'eye' | 'grip' | 'flask';

interface Props {
  name: IconName;
  size?: 16 | 20 | 24;
  className?: string;
  style?: React.CSSProperties;
}

export default function Icon({ name, size = 20, className = '', style }: Props) {
  const sizeClass = size === 16 ? ' ad-icon--16' : size === 24 ? ' ad-icon--24' : '';
  return (
    <svg className={`ad-icon${sizeClass} ${className}`.trim()} aria-hidden="true" style={style}>
      <use href={`#i-${name}`} />
    </svg>
  );
}
