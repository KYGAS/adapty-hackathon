import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import Icon, { type IconName } from './Icon';
import type { Health } from '../lib/types';

const NAV: Array<[IconName, string, string, string?]> = [
  ['overview', 'Overview', '/stub/Overview'],
  ['analytics', 'Analytics', '/stub/Analytics'],
  ['users', 'Profiles & Segments', '/stub/Profiles'],
  ['box', 'Products', '/stub/Products'],
  ['flows', 'Flows & Paywalls', '/stub/Flows'],
  ['pin', 'Placements', '/placements/flows'],
  ['message', 'Retention Messaging', '/stub/Retention Messaging'],
  ['ab', 'A/B tests', '/ab-tests/flows'],
  ['flask', 'Experiment Referee', '/referee', 'New'],
  ['rocket', 'AI Growth Advisor', '/stub/AI Growth Advisor'],
  ['refund', 'Refund saver', '/stub/Refund saver'],
  ['dollar', 'Finance', '/stub/Finance'],
  ['plug', 'Integrations', '/stub/Integrations'],
];

export default function Shell({ health, children }: { health: Health | null; children: ReactNode }) {
  return (
    <div className="ad-app">
      <aside className="ad-sidebar">
        <div>
          <div className="ad-sidebar__logo">
            <div className="ad-sidebar__brand">
              <span style={{ display: 'inline-flex', width: 20, height: 20, borderRadius: '50% 50% 50% 4px', background: '#111' }} />
              adapty <Icon name="chevron-down" size={16} style={{ color: 'var(--black-600)' }} />
            </div>
            <button className="ad-sidebar__collapse" data-hint="Collapse menu" data-hint-dark="">
              <Icon name="chevrons-left" />
            </button>
          </div>
        </div>
        <nav className="ad-sidebar__scroll">
          {NAV.map(([icon, label, href, badge]) => (
            <NavLink key={href} to={href} className={({ isActive }) => `ad-nav-item ${isActive ? 'is-selected' : ''}`}>
              <Icon name={icon} />
              <span className="ad-nav-item__label">{label}</span>
              {badge && <span className="ad-badge ad-badge--blue">{badge}</span>}
            </NavLink>
          ))}
        </nav>
        <div className="ad-sidebar__widget">
          <div className="ad-onboarding">
            <div className="ad-row" style={{ justifyContent: 'space-between' }}>
              <span className="ad-medium">Getting started</span>
              <Icon name="chevron-down" size={16} />
            </div>
            <div className="ad-stepper">
              {[1, 2, 3, 4, 5].map((i) => (
                <span key={i} className="is-done" />
              ))}
              <span />
              <span />
            </div>
            <div className="ad-stack ad-stack--8" style={{ gap: 6 }}>
              <span className="ad-caption" style={{ color: 'var(--blackPrimary)' }}>Connect app stores</span>
              <span className="ad-caption" style={{ color: 'var(--blackPrimary)' }}>Setup server notifications</span>
              <span className="ad-caption" style={{ color: 'var(--blackPrimary)' }}>Install Adapty SDK</span>
            </div>
          </div>
        </div>
      </aside>

      <header className="ad-header">
        <div className="ad-header__inner">
          <div className="ad-menu-anchor">
            <div className="ad-app-switcher" data-menu-trigger="">
              <span className="ad-app-switcher__avatar">L</span>
              <span className="ad-app-switcher__name">Lumen - AI Photo Editor (Hackathon)</span>
              <Icon name="chevron-down" size={16} />
              {health && (
                <span
                  className={`ad-pill rf-mode-pill ${health.adapty_mode === 'live' ? 'ad-pill--green' : 'ad-pill--violet'}`}
                  data-hint={health.adapty_mode === 'live' ? 'Reading the Lumen app through the Adapty developer API' : 'Serving captured Adapty API answers from the backend'}
                >
                  {health.adapty_mode === 'live' ? 'Live data' : 'Mock data'}
                </span>
              )}
            </div>
            <ul className="ad-menu ad-menu--left" style={{ width: 360, borderRadius: 12 }}>
              <li className="ad-menu__item">
                <span className="ad-app-switcher__avatar" style={{ width: 24, height: 24, flexBasis: 24 }}>L</span>
                Lumen - AI Photo Editor (Hackathon)
              </li>
            </ul>
          </div>
          <nav className="ad-header__nav">
            <div className="ad-bell" data-hint="No unread notifications">
              <Icon name="bell" />
            </div>
            <a className="ad-header__link">Help</a>
            <a className="ad-header__link">App settings</a>
            <a className="ad-header__link">Account</a>
          </nav>
        </div>
      </header>

      <main className="ad-content">{children}</main>
    </div>
  );
}
