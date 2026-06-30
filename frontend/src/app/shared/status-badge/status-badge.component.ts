import { NgClass } from '@angular/common';
import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  imports: [NgClass],
  template: '<span class="status-badge" [ngClass]="tone" [attr.data-status]="label">{{ label || "UNKNOWN" }}</span>'
})
export class StatusBadgeComponent {
  @Input() label = 'UNKNOWN';
  @Input() tone: 'success' | 'warning' | 'danger' | 'neutral' = 'neutral';
}
