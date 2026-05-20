import { Component } from '@angular/core';
import { NgClass, NgFor } from '@angular/common';
import { ToastService } from './toast.service';

@Component({
  selector: 'app-toast-container',
  standalone: true,
  imports: [NgClass, NgFor],
  template: `
    <div class="toast-region" aria-live="polite" aria-atomic="true">
      <button
        *ngFor="let message of toast.messages()"
        type="button"
        class="toast"
        [ngClass]="message.tone"
        (click)="toast.dismiss(message.id)">
        {{ message.text }}
      </button>
    </div>
  `
})
export class ToastComponent {
  constructor(readonly toast: ToastService) {}
}
