import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-metric-card',
  standalone: true,
  template: `
    <article class="metric-card">
      <span>{{ label }}</span>
      <strong>{{ value }}</strong>
      <p>{{ detail }}</p>
    </article>
  `
})
export class MetricCardComponent {
  @Input({ required: true }) label = '';
  @Input() value: string | number = '--';
  @Input() detail = '';
}
