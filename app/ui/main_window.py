"""
Main Window Shell for Smart Clinical Lab.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from sqlalchemy.orm import Session

from app.services import AuthService
from app.security import SessionContext
from app.ui.auth_dialogs import FirstRunDialog, LoginDialog
from app.ui.views import (
    DashboardView, PatientView, OrderView, ResultView, ReportView,
    TestCatalogView, UserManagementView, AuditLogView, BackupRestoreView, SettingsView
)


class MainWindow(tk.Tk):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self.auth_svc = AuthService(session)

        self.title("Smart Clinical Lab - Laboratory Management System")
        self.geometry("1100x700")
        self.minsize(900, 600)

        self.views = {}
        self.current_view = None

        self.withdraw()  # Hide main window during first run / login
        self.after(100, self._check_first_run_and_login)

    def _check_first_run_and_login(self):
        if self.auth_svc.is_first_run():
            FirstRunDialog(self, self.session, self._show_login)
        else:
            self._show_login()

    def _show_login(self):
        LoginDialog(self, self.session, self._on_login_success)

    def _on_login_success(self, user):
        self.deiconify()
        self._build_ui()
        self.show_view("Dashboard")

    def _build_ui(self):
        # Top Bar
        top_bar = ttk.Frame(self, padding=8, relief=tk.RAISED)
        top_bar.pack(fill=tk.X, side=tk.TOP)

        lbl_title = ttk.Label(top_bar, text="SMART CLINICAL LAB", font=("Helvetica", 12, "bold"), foreground="#003366")
        lbl_title.pack(side=tk.LEFT, padx=10)

        ctx = SessionContext.get_instance()
        role_str = ctx.roles[0] if ctx.roles else "User"
        user_info = f"Logged in as: {ctx.display_name or 'User'} ({role_str})" if ctx.current_user_id else ""
        lbl_user = ttk.Label(top_bar, text=user_info, font=("Helvetica", 9))
        lbl_user.pack(side=tk.RIGHT, padx=10)

        btn_logout = ttk.Button(top_bar, text="Logout", command=self._logout)
        btn_logout.pack(side=tk.RIGHT, padx=5)

        # Main Layout Container
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        # Sidebar Navigation
        sidebar = ttk.Frame(container, padding=10, width=180, relief=tk.RAISED)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        container.columnconfigure(1, weight=1)

        # Main Content Area
        self.content_area = ttk.Frame(container, padding=10)
        self.content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Register Navigation Items
        nav_items = [
            ("Dashboard", DashboardView, "dashboard_view"),
            ("Patients", PatientView, "patient_view"),
            ("Orders", OrderView, "order_create"),
            ("Results", ResultView, "result_entry"),
            ("Reports", ReportView, "report_generate"),
            ("Test Catalog", TestCatalogView, "test_manage"),
            ("Users", UserManagementView, "user_manage"),
            ("Audit Log", AuditLogView, "audit_view"),
            ("Backup/Restore", BackupRestoreView, "backup_manage"),
            ("Settings", SettingsView, "settings_manage"),
        ]

        for label, view_cls, perm_code in nav_items:
            if ctx.has_permission(perm_code) or ctx.is_admin():
                view_instance = view_cls(self.content_area, self.session)
                self.views[label] = view_instance

                btn = ttk.Button(
                    sidebar,
                    text=label,
                    command=lambda l=label: self.show_view(l)
                )
                btn.pack(fill=tk.X, pady=3)

    def show_view(self, name: str):
        if name in self.views:
            if self.current_view:
                self.current_view.pack_forget()

            self.current_view = self.views[name]
            self.current_view.pack(fill=tk.BOTH, expand=True)
            self.current_view.refresh()

    def _logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to log out?"):
            self.auth_svc.logout()
            self.withdraw()
            for v in self.views.values():
                v.destroy()
            self.views.clear()
            self._show_login()
