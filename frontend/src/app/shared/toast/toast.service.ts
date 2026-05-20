import { Injectable, signal } from '@angular/core';

export type ToastTone = 'success' | 'warning' | 'danger' | 'info';

export interface ToastMessage {
  id: number;
  tone: ToastTone;
  text: string;
}

@Injectable({ providedIn: 'root' })
export class ToastService {
  readonly messages = signal<ToastMessage[]>([]);
  private nextId = 1;

  show(text: string, tone: ToastTone = 'info'): void {
    const message: ToastMessage = {
      id: this.nextId,
      tone,
      text
    };
    this.nextId += 1;
    this.messages.update((messages) => [...messages, message]);
    window.setTimeout(() => this.dismiss(message.id), 4500);
  }

  dismiss(id: number): void {
    this.messages.update((messages) => messages.filter((message) => message.id !== id));
  }
}
