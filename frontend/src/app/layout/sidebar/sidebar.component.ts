import { Component } from '@angular/core';
import { NgFor } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';

interface NavItem {
  label: string;
  route: string;
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [NgFor, RouterLink, RouterLinkActive],
  template: `
    <aside class="sidebar" aria-label="KALYX navigation">
      <div class="brand-block">
        <div class="brand-mark" aria-hidden="true"><span></span></div>
        <div>
          <p>KALYX</p>
          <h1>Integrity Console</h1>
        </div>
      </div>

      <nav class="side-nav" aria-label="Primary">
        <a
          *ngFor="let item of navItems"
          [routerLink]="item.route"
          routerLinkActive="active"
          [routerLinkActiveOptions]="{ exact: true }">
          <span aria-hidden="true"></span>
          {{ item.label }}
        </a>
      </nav>

      <div class="sidebar-note">
        <span>Backend Authority</span>
        <strong>FastAPI REST API</strong>
      </div>
    </aside>
  `
})
export class SidebarComponent {
  readonly navItems: NavItem[] = [
    { label: 'Overview', route: '/overview' },
    { label: 'Ledger', route: '/ledger' },
    { label: 'Verification', route: '/verification' },
    { label: 'Ingestion', route: '/ingestion' },
    { label: 'Detection', route: '/detection' },
    { label: 'Alerts', route: '/alerts' },
    { label: 'Evidence', route: '/evidence' }
  ];
}
