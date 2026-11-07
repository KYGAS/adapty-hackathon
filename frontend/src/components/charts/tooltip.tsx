import { useCallback, useState, type ReactNode } from 'react';

interface TooltipState {
  x: number;
  y: number;
  content: ReactNode;
}

/** One floating tooltip per chart: show(event, content) on hover, hide() on leave. */
export function useTooltip() {
  const [tip, setTip] = useState<TooltipState | null>(null);
  const show = useCallback((e: React.MouseEvent, content: ReactNode) => setTip({ x: e.clientX + 12, y: e.clientY + 12, content }), []);
  const hide = useCallback(() => setTip(null), []);
  const element = tip ? (
    <div className="rf-tooltip" style={{ left: Math.min(tip.x, window.innerWidth - 240), top: tip.y }}>
      {tip.content}
    </div>
  ) : null;
  return { show, hide, element };
}
