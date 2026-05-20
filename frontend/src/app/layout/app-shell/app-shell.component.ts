import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SidebarComponent } from '../sidebar/sidebar.component';
import { TopbarComponent } from '../topbar/topbar.component';
import { ToastComponent } from '../../shared/toast/toast.component';

@Component({
  selector: 'app-app-shell',
  standalone: true,
  imports: [RouterOutlet, SidebarComponent, TopbarComponent, ToastComponent],
  template: `
    <div class="app-shell">
      <app-sidebar />
      <section class="workspace">
        <app-topbar />
        <main class="content">
          <router-outlet />
        </main>
      </section>
      <app-toast-container />
    </div>
  `
})
export class AppShellComponent {}
