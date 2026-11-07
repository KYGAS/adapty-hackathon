import { Link, useNavigate } from 'react-router-dom';
import Icon from './Icon';
import VariantTable from './VariantTable';
import VerdictText from './VerdictText';
import { toast } from './common';
import { durationBetween, fmtDate } from '../lib/format';
import type { AdaptyMetricsRow, AdaptyTestDetail, AdaptyTestListed, Verdict } from '../lib/types';

interface Props {
  test: AdaptyTestListed;
  detail: AdaptyTestDetail | null;
  metrics: AdaptyMetricsRow | null; // row from GET ab-tests/metrics/ (items = arms)
  verdict?: Verdict | null;
  audience: string;
  priority?: number;
  audienceIcon?: boolean;
}

export default function TestCard({ test, detail, metrics, verdict, audience, priority, audienceIcon }: Props) {
  const navigate = useNavigate();
  const metricsHref = `/ab-tests/flows/${test.ab_test_id}/metrics`;
  const refereeHref = `/referee/${test.ab_test_id}`;
  const started = test.started_at ? `Started ${fmtDate(test.started_at)} (${durationBetween(test.started_at, test.stopped_at)})` : null;
  const actions = () => {
    const kebab = (items: Array<[string, () => void, boolean?]>) => (
      <div className="ad-menu-anchor">
        <button className="ad-icon-btn" data-menu-trigger="" aria-label="More">
          <Icon name="more" />
        </button>
        <ul className="ad-menu">
          {items.map(([label, fn, danger]) => (
            <li key={label} className={`ad-menu__item ${danger ? 'ad-menu__item--danger' : ''}`} onClick={fn}>
              {label}
            </li>
          ))}
        </ul>
      </div>
    );
    if (test.state === 'live') {
      return (
        <>
          <Link className="ad-btn ad-btn--v2 ad-btn--with-icon" to={metricsHref}><Icon name="metrics" />View metrics</Link>
          <button className="ad-btn ad-btn--v2 ad-btn--with-icon" onClick={() => navigate(refereeHref)} data-hint="Stopping goes through the Referee: it shows the evidence and the dry-run command first">
            <Icon name="stop" />Stop A/B test
          </button>
          {kebab([
            ['Modify', () => toast('Modify opens the create form in Adapty. Not part of this demo.', 'info')],
            ['Duplicate', () => toast('A/B test duplicated as draft (demo)', 'success')],
          ])}
        </>
      );
    }
    if (test.state === 'completed') {
      return (
        <>
          <Link className="ad-btn ad-btn--v2 ad-btn--with-icon" to={metricsHref}><Icon name="metrics" />View metrics</Link>
          <Link className="ad-btn ad-btn--v2 ad-btn--with-icon" to={refereeHref}><Icon name="flask" />Audit</Link>
          {kebab([
            ['Duplicate', () => toast('A/B test duplicated as draft (demo)', 'success')],
            ['Archive', () => toast('Archiving is a write; approve it in the Referee.', 'info')],
          ])}
        </>
      );
    }
    if (test.state === 'draft') {
      return (
        <>
          <button className="ad-btn ad-btn--v2 ad-btn--with-icon" onClick={() => toast('Edit opens the create form in Adapty. Not part of this demo.', 'info')}><Icon name="pencil" />Edit</button>
          <Link className="ad-btn ad-btn--v2 ad-btn--with-icon" to={refereeHref}><Icon name="play" />Run A/B test</Link>
          {kebab([
            ['Duplicate', () => toast('A/B test duplicated as draft (demo)', 'success')],
            ['Archive', () => toast('Archiving is a write; approve it in the Referee.', 'info')],
          ])}
        </>
      );
    }
    return kebab([['Duplicate', () => toast('A/B test duplicated as draft (demo)', 'success')]]);
  };
  const goal = detail?.goal || 'No goal set';
  return (
    <article className="ad-card">
      <div className="ad-card__header">
        <div className="ad-card__header-main">
          <span className="ad-tile">
            <Icon name={audienceIcon ? 'users' : 'ab'} />
            {audienceIcon && priority !== undefined && (
              <span className="ad-tile__priority"><span className="ad-tag">#{priority}</span></span>
            )}
          </span>
          <div style={{ minWidth: 0 }}>
            <div className="ad-card__title-row">
              {audienceIcon && (
                <>
                  <h5 className="ad-h5 ad-bold ad-hint" data-hint-title={audience} data-hint="Audience segment">{audience}</h5>
                  <h5 className="ad-h5">·</h5>
                </>
              )}
              <h5 className="ad-h5 ad-ellipsis ad-hint" data-hint-title="Goal" data-hint={goal}>{test.title}</h5>
              <span className="ad-tag ad-tag--violet ad-hint" data-hint-title="Flow A/B test" data-hint="This A/B test runs on a single placement.">A/B test</span>
            </div>
            <div className="ad-card__meta">
              {!audienceIcon && (
                <span className="ad-card__meta-item">
                  <Icon name="users" />
                  <span className="ad-hint" data-hint="Audience">{audience}</span>
                </span>
              )}
              <Link className="ad-card__meta-item ad-link--secondary ad-link--small" to={`/placements/flows/${test.placement.placement_id}`}>
                <Icon name="pin" />{test.placement.title}
              </Link>
              {started && (
                <span className="ad-card__meta-item"><Icon name="clock" />{started}</span>
              )}
              {verdict && (
                <Link className="ad-card__meta-item" to={refereeHref} style={{ textDecoration: 'none' }}>
                  <VerdictText verdict={verdict} />
                </Link>
              )}
            </div>
          </div>
        </div>
        <div className="ad-card__actions">{actions()}</div>
      </div>
      {detail && <VariantTable arms={detail.flows} rows={metrics?.items ?? []} total={metrics} />}
    </article>
  );
}
