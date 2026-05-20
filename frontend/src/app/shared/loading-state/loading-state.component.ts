import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-loading-state',
  standalone: true,
  template: `
    <div class="loading-state" [attr.aria-label]="label">
      <span></span>
      <span></span>
      <span></span>
    </div>
  `
})
export class LoadingStateComponent {
  @Input() label = 'Loading';
}
