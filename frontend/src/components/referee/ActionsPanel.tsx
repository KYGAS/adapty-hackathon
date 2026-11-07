import { useState } from 'react';
import Icon from '../Icon';
import { Modal, toast } from '../common';
import { ApiError, getHealth, referee } from '../../lib/api';
import type { ActionPreview, ExecuteResult } from '../../lib/types';

const RISK_LABEL = { none: 'No change', reversible: 'Reversible', irreversible: 'Irreversible' } as const;

export function ApprovalModal({ testId, action, open, onClose, onDone }: {
  testId: string;
  action: ActionPreview | null;
  open: boolean;
  onClose: () => void;
  onDone: (result: ExecuteResult) => void;
}) {
  const [approver, setApprover] = useState('');
  const [reviewed, setReviewed] = useState(false);
  const [busy, setBusy] = useState(false);
  const health = getHealth();
  if (!action) return null;
  const canRun = approver.trim().length > 1 && (action.risk !== 'irreversible' || reviewed) && !busy;
  const run = async () => {
    setBusy(true);
    try {
      const result = await referee.execute({ test_id: testId, action_id: action.id, approved: true, approver: approver.trim() });
      toast(result.status === 'executed' ? `Done: ${action.title}` : `Recorded: ${result.status.replace('_', ' ')}`, 'success');
      onDone(result);
      onClose();
    } catch (err) {
      const e = err as ApiError;
      const detail = (e.body as { detail?: { message?: string } })?.detail;
      toast(detail?.message || e.message || 'The action was refused', e.status === 403 ? 'warning' : 'error');
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={action.title}
      info={action.description}
      footer={
        <>
          <button className="ad-btn ad-btn--secondary" onClick={onClose}>Cancel</button>
          <button className={`ad-btn ${action.risk === 'irreversible' ? 'ad-btn--danger' : 'ad-btn--primary'} ${busy ? 'is-loading' : ''}`} disabled={!canRun} onClick={run}>
            {busy && <span className="ad-spinner" />}
            Approve and run
          </button>
        </>
      }
    >
      <h5 className="ad-h5 rf-mb-8">What will run</h5>
      <pre className="rf-command">{action.cli_command}</pre>
      <p className="ad-caption" style={{ margin: '8px 0 16px' }}>
        API equivalent: {action.api_method} {action.api_path} {JSON.stringify(action.api_body)}
      </p>
      {health && health.adapty_mode === 'live' && !health.live_writes_allowed && (
        <div className="ad-inline-alert rf-mb-16">
          <Icon name="warning" />
          Live writes are off on this backend. The approval is logged, nothing reaches Adapty until REFEREE_ALLOW_LIVE_WRITES is true.
        </div>
      )}
      <div className="ad-field">
        <div className="ad-field__label">
          <span className="ad-field__label-text">Approved by</span>
          <span className="ad-field__required">Required</span>
        </div>
        <input className="ad-input" placeholder="Your name" value={approver} onChange={(e) => setApprover(e.target.value)} />
      </div>
      {action.risk === 'irreversible' && (
        <label className="ad-checkbox" style={{ marginTop: 8 }}>
          <input type="checkbox" checked={reviewed} onChange={(e) => setReviewed(e.target.checked)} />
          <span className="ad-checkbox__box">
            <svg viewBox="0 0 20 20"><path d="m4 10.5 4 4 8-9" /></svg>
          </span>
          I read the dossier. This stops the test for the whole audience and cannot be undone.
        </label>
      )}
    </Modal>
  );
}

export default function ActionsPanel({ testId, actions, onChanged }: { testId: string; actions: ActionPreview[]; onChanged: () => void }) {
  const [selected, setSelected] = useState<ActionPreview | null>(null);
  const dryRun = async (action: ActionPreview) => {
    try {
      const result = await referee.execute({ test_id: testId, action_id: action.id, approved: false, approver: 'dry-run' });
      toast(result.status === 'dry_run' ? 'Dry run recorded in the decision log. Nothing was changed.' : 'Nothing to run for this action.', 'info');
      onChanged();
    } catch (err) {
      toast((err as Error).message, 'error');
    }
  };
  return (
    <div className="ad-panel">
      <h4 className="ad-h4 rf-mb-8">Actions</h4>
      <p className="ad-caption rf-mb-16">Every action is a dry-run command first. Nothing touches Adapty without an approval here.</p>
      <div className="ad-stack ad-stack--8">
        {actions.map((a) => (
          <div key={a.id} className={`rf-action ${a.recommended ? 'is-recommended' : ''}`}>
            <div className="rf-action__row">
              <div>
                <div className="ad-row" style={{ gap: 8 }}>
                  <span className="ad-h5">{a.title}</span>
                  {a.recommended && <span className="ad-tag ad-tag--violet">Recommended</span>}
                </div>
                <div className="ad-caption">{a.description}</div>
              </div>
              <span className={`ad-caption-sm rf-nowrap rf-risk--${a.risk}`}>{RISK_LABEL[a.risk]}</span>
            </div>
            {a.cli_command && (
              <>
                <pre className="rf-command">{a.cli_command}</pre>
                <div className="ad-row" style={{ gap: 8 }}>
                  <button className="ad-btn ad-btn--v2 ad-btn--with-icon" onClick={() => dryRun(a)}>
                    <Icon name="eye" />
                    Dry run
                  </button>
                  <button className={`ad-btn ad-btn--v2 ad-btn--with-icon ${a.risk === 'irreversible' ? 'rf-risk--irreversible' : ''}`} onClick={() => setSelected(a)}>
                    <Icon name={a.kind === 'start_draft' ? 'play' : 'stop'} />
                    Approve and run
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
      <ApprovalModal testId={testId} action={selected} open={!!selected} onClose={() => setSelected(null)} onDone={onChanged} />
    </div>
  );
}
