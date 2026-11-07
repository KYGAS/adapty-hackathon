import { useState } from 'react';
import Icon from '../Icon';
import Markdown from './Markdown';
import { getHealth, referee } from '../../lib/api';
import type { Narration } from '../../lib/types';

const PROVIDERS = [
  ['auto', 'Auto'],
  ['cli', 'Claude Code CLI (subscription)'],
  ['api', 'Anthropic API (token)'],
  ['template', 'Deterministic template'],
] as const;

export default function MemoPanel({ testId }: { testId: string }) {
  const [provider, setProvider] = useState<string>('auto');
  const [narration, setNarration] = useState<Narration | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const health = getHealth();
  const write = async () => {
    setBusy(true);
    setError(null);
    try {
      setNarration(await referee.memo(testId, provider === 'auto' ? undefined : provider));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="ad-panel">
      <div className="ad-row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h4 className="ad-h4">Executive memo</h4>
          <p className="ad-caption">The LLM narrates the dossier. It never computes: a guard rejects any number that is not in the dossier.</p>
        </div>
        <div className="ad-row" style={{ gap: 8 }}>
          <select className="ad-input" style={{ height: 36, width: 240 }} value={provider} onChange={(e) => setProvider(e.target.value)}>
            {PROVIDERS.map(([value, label]) => (
              <option key={value} value={value} disabled={(value === 'api' && !health?.anthropic_api_key_present) || (value === 'cli' && !health?.claude_cli_found)}>
                {label}
              </option>
            ))}
          </select>
          <button className={`ad-btn ad-btn--primary ${busy ? 'is-loading' : ''}`} disabled={busy} onClick={write}>
            {busy && <span className="ad-spinner" />}
            {narration ? 'Rewrite memo' : 'Write memo'}
          </button>
        </div>
      </div>
      {error && <div className="rf-error rf-mt-24">{error}</div>}
      {narration && (
        <div className="rf-mt-24">
          <div className="ad-row rf-mb-8" style={{ gap: 8, flexWrap: 'wrap' }}>
            <span className="ad-pill ad-pill--grayborder">{narration.provider}{narration.model ? ` · ${narration.model}` : ''}</span>
            <span className={`ad-pill ${narration.guard_passed ? 'ad-pill--green' : 'ad-pill--red'}`}>
              {narration.guard_passed ? 'Number guard passed' : 'Number guard rejected the model'}
            </span>
            {narration.fallback_used && <span className="ad-pill ad-pill--yellow">Template fallback</span>}
            <span className="ad-caption-sm">{narration.attempts} attempt{narration.attempts === 1 ? '' : 's'} · {(narration.elapsed_ms / 1000).toFixed(1)} s</span>
          </div>
          {narration.guard_violations.length > 0 && (
            <div className="ad-inline-alert rf-mb-16">
              <Icon name="warning" />
              {narration.guard_violations.slice(0, 3).join(' | ')}
            </div>
          )}
          <h5 className="ad-h5">{narration.memo.headline}</h5>
          <p className="ad-body rf-mb-8">{narration.memo.summary}</p>
          <Markdown text={narration.memo.memo_markdown} />
          {narration.memo.risks.length > 0 && (
            <>
              <h5 className="ad-h5 rf-mt-24">Risks</h5>
              <ul className="rf-reasons">{narration.memo.risks.map((r, i) => <li key={i}>{r}</li>)}</ul>
            </>
          )}
          {narration.memo.next_steps.length > 0 && (
            <>
              <h5 className="ad-h5 rf-mt-24">Next steps</h5>
              <ul className="rf-reasons">{narration.memo.next_steps.map((r, i) => <li key={i}>{r}</li>)}</ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}
