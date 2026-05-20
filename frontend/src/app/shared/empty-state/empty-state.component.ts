import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  template: `
    <section class="empty-state">
      <strong>{{ title }}</strong>
      <p>{{ message }}</p>
    </section>
  `
})
export class EmptyStateComponent {
  @Input() title = 'No data';
  @Input() message = 'There is nothing to display yet.';
}
