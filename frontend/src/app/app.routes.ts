import { Routes } from '@angular/router';
import { AppShellComponent } from './layout/app-shell/app-shell.component';
import { OverviewComponent } from './features/overview/overview.component';
import { LedgerComponent } from './features/ledger/ledger.component';
import { VerificationComponent } from './features/verification/verification.component';
import { IngestionComponent } from './features/ingestion/ingestion.component';
import { DetectionComponent } from './features/detection/detection.component';
import { AlertsComponent } from './features/alerts/alerts.component';
import { EvidenceComponent } from './features/evidence/evidence.component';

export const routes: Routes = [
  {
    path: '',
    component: AppShellComponent,
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'overview' },
      { path: 'overview', component: OverviewComponent },
      { path: 'ledger', component: LedgerComponent },
      { path: 'verification', component: VerificationComponent },
      { path: 'ingestion', component: IngestionComponent },
      { path: 'detection', component: DetectionComponent },
      { path: 'alerts', component: AlertsComponent },
      { path: 'evidence', component: EvidenceComponent }
    ]
  },
  { path: '**', redirectTo: 'overview' }
];
