"""
Tkinter UI Dialogs for First-Run Setup and User Login.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from sqlalchemy.orm import Session
from app.services import AuthService
from app.repositories import SettingRepository


class FirstRunDialog(tk.Toplevel):
    def __init__(self, parent, session: Session, on_success_callback):
        super().__init__(parent)
        self.session = session
        self.on_success = on_success_callback
        self.auth_svc = AuthService(session)
        self.setting_repo = SettingRepository(session)

        self.title("Smart Clinical Lab - First-Run Setup")
        self.geometry("500x550")
        self.resizable(False, False)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        lbl_header = ttk.Label(
            main_frame,
            text="Welcome to Smart Clinical Lab",
            font=("Helvetica", 14, "bold")
        )
        lbl_header.pack(anchor=tk.W, pady=(0, 5))

        lbl_sub = ttk.Label(
            main_frame,
            text="Initial system setup: Create Administrator and Lab Details.",
            font=("Helvetica", 9)
        )
        lbl_sub.pack(anchor=tk.W, pady=(0, 15))

        # Admin Details Group
        admin_group = ttk.LabelFrame(main_frame, text=" Initial Administrator Account ", padding=10)
        admin_group.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(admin_group, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.ent_username = ttk.Entry(admin_group, width=30)
        self.ent_username.insert(0, "admin")
        self.ent_username.grid(row=0, column=1, sticky=tk.W, pady=4)

        ttk.Label(admin_group, text="Display Name:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.ent_display_name = ttk.Entry(admin_group, width=30)
        self.ent_display_name.insert(0, "Laboratory Administrator")
        self.ent_display_name.grid(row=1, column=1, sticky=tk.W, pady=4)

        ttk.Label(admin_group, text="Password:").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.ent_password = ttk.Entry(admin_group, width=30, show="*")
        self.ent_password.grid(row=2, column=1, sticky=tk.W, pady=4)

        ttk.Label(admin_group, text="Confirm Password:").grid(row=3, column=0, sticky=tk.W, pady=4)
        self.ent_confirm = ttk.Entry(admin_group, width=30, show="*")
        self.ent_confirm.grid(row=3, column=1, sticky=tk.W, pady=4)

        # Lab Details Group
        lab_group = ttk.LabelFrame(main_frame, text=" Laboratory Identity ", padding=10)
        lab_group.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(lab_group, text="Lab Name:").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.ent_lab_name = ttk.Entry(lab_group, width=30)
        self.ent_lab_name.insert(0, "Smart Clinical Laboratory")
        self.ent_lab_name.grid(row=0, column=1, sticky=tk.W, pady=4)

        ttk.Label(lab_group, text="Address / Location:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.ent_lab_addr = ttk.Entry(lab_group, width=30)
        self.ent_lab_addr.insert(0, "Medical Center Road, Kochi, Kerala")
        self.ent_lab_addr.grid(row=1, column=1, sticky=tk.W, pady=4)

        ttk.Label(lab_group, text="Phone Number:").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.ent_lab_phone = ttk.Entry(lab_group, width=30)
        self.ent_lab_phone.insert(0, "+91 484 2345678")
        self.ent_lab_phone.grid(row=2, column=1, sticky=tk.W, pady=4)

        btn_submit = ttk.Button(main_frame, text="Complete Setup & Save", command=self._save_first_run)
        btn_submit.pack(anchor=tk.E, pady=10)

    def _save_first_run(self):
        username = self.ent_username.get().strip()
        disp_name = self.ent_display_name.get().strip()
        pwd = self.ent_password.get()
        confirm = self.ent_confirm.get()

        if not username or not pwd:
            messagebox.showerror("Error", "Username and Password are required.", parent=self)
            return

        if pwd != confirm:
            messagebox.showerror("Error", "Passwords do not match.", parent=self)
            return

        try:
            self.auth_svc.create_initial_admin(username, pwd, disp_name)
            self.setting_repo.set("lab_name", self.ent_lab_name.get().strip())
            self.setting_repo.set("lab_address", self.ent_lab_addr.get().strip())
            self.setting_repo.set("lab_phone", self.ent_lab_phone.get().strip())

            messagebox.showinfo("Success", "First-run setup completed successfully! Please login.", parent=self)
            self.destroy()
            if self.on_success:
                self.on_success()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)


class LoginDialog(tk.Toplevel):
    def __init__(self, parent, session: Session, on_login_success):
        super().__init__(parent)
        self.session = session
        self.on_login_success = on_login_success
        self.auth_svc = AuthService(session)

        self.title("Smart Clinical Lab - Login")
        self.geometry("400x300")
        self.resizable(False, False)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self, padding=25)
        frame.pack(fill=tk.BOTH, expand=True)

        lbl_hdr = ttk.Label(frame, text="User Login", font=("Helvetica", 14, "bold"))
        lbl_hdr.pack(anchor=tk.W, pady=(0, 15))

        ttk.Label(frame, text="Username:").pack(anchor=tk.W, pady=(5, 2))
        self.ent_user = ttk.Entry(frame, width=35)
        self.ent_user.pack(fill=tk.X, pady=(0, 10))
        self.ent_user.focus_set()

        ttk.Label(frame, text="Password:").pack(anchor=tk.W, pady=(5, 2))
        self.ent_pass = ttk.Entry(frame, width=35, show="*")
        self.ent_pass.pack(fill=tk.X, pady=(0, 15))

        self.ent_pass.bind("<Return>", lambda e: self._attempt_login())

        btn_login = ttk.Button(frame, text="Login", command=self._attempt_login)
        btn_login.pack(anchor=tk.E)

    def _attempt_login(self):
        username = self.ent_user.get().strip()
        password = self.ent_pass.get()

        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password.", parent=self)
            return

        user = self.auth_svc.login(username, password)
        if user:
            self.destroy()
            if self.on_login_success:
                self.on_login_success(user)
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.", parent=self)
