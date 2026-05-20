import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-json-viewer',
  standalone: true,
  template: `
    <details class="json-viewer" [open]="open">
      <summary>{{ label }}</summary>
      <pre>{{ serialized }}</pre>
    </details>
  `
})
export class JsonViewerComponent {
  @Input() label = 'Raw JSON';
  @Input() value: unknown = null;
  @Input() open = false;

  get serialized(): string {
    return JSON.stringify(this.value ?? {}, null, 2);
  }
}
