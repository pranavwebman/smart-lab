"""
Modular Views for Dashboard, Patients, Orders, Results, Reports, Test Catalog, Users, Audit, Backup, and Settings.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import (
    Patient, Order, Test, TestCategory, TestParameter, ReferenceRange, User, OrderStatusEnum, FlagEnum
)
from app.services import (
    PatientService, TestService, OrderService, ResultService, VerificationService, BillingService, BackupService
)
from app.repositories import AuditRepository, SettingRepository, OrderRepository
from app.reports import ReportService
from app.security import SessionContext


class BaseView(ttk.Frame):
    def __init__(self, parent, session: Session, **kwargs):
        super().__init__(parent, **kwargs)
        self.session = session

    def refresh(self):
        pass


class DashboardView(BaseView):
    def __init__(self, parent, session: Session):
        super().__init__(parent, session)
        self._build_ui()

    def _build_ui(self):
        label = ttk.Label(self, text="Operational Dashboard", font=("Helvetica", 16, "bold"))
        label.pack(anchor=tk.W, pady=10, padx=10)

        # Stat cards frame
        cards_frame = ttk.Frame(self)
        cards_frame.pack(fill=tk.X, padx=10, pady=10)

        self.lbl_patients = self._create_card(cards_frame, "Today's Patients", "0", 0)
        self.lbl_orders = self._create_card(cards_frame, "Today's Orders", "0", 1)
        self.lbl_pending = self._create_card(cards_frame, "Pending Results", "0", 2)
        self.lbl_unverified = self._create_card(cards_frame, "Awaiting Verification", "0", 3)

        # Recent Orders Table
        lbl_recent = ttk.Label(self, text="Recent Orders", font=("Helvetica", 12, "bold"))
        lbl_recent.pack(anchor=tk.W, padx=10, pady=(15, 5))

        cols = ("order_num", "patient_name", "date", "status", "total")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=10)
        self.tree.heading("order_num", text="Order #")
        self.tree.heading("patient_name", text="Patient Name")
        self.tree.heading("date", text="Date")
        self.tree.heading("status", text="Status")
        self.tree.heading("total", text="Total (INR)")

        self.tree.column("order_num", width=120)
        self.tree.column("patient_name", width=200)
        self.tree.column("date", width=150)
        self.tree.column("status", width=120)
        self.tree.column("total", width=100)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def _create_card(self, parent, title, value, col):
        f = ttk.LabelFrame(parent, text=f" {title} ", padding=10)
        f.grid(row=0, column=col, padx=5, pady=5, sticky="nsew")
        parent.columnconfigure(col, weight=1)
        lbl = ttk.Label(f, text=value, font=("Helvetica", 18, "bold"), foreground="#003366")
        lbl.pack(anchor=tk.CENTER)
        return lbl

    def refresh(self):
        order_repo = OrderRepository(self.session)
        orders = order_repo.search_orders(limit=50)

        today_str = datetime.now().strftime("%Y-%m-%d")
        today_patients = set()
        today_orders_cnt = 0
        pending_cnt = 0
        unverified_cnt = 0

        for item in self.tree.get_children():
            self.tree.delete(item)

        for o in orders:
            o_date_str = o.order_date.strftime("%Y-%m-%d")
            if o_date_str == today_str:
                today_patients.add(o.patient_id)
                today_orders_cnt += 1

            if o.status in [OrderStatusEnum.REGISTERED.value, OrderStatusEnum.SAMPLE_COLLECTED.value, OrderStatusEnum.PROCESSING.value, OrderStatusEnum.RESULTS_PENDING.value]:
                pending_cnt += 1
            elif o.status == OrderStatusEnum.RESULTS_ENTERED.value:
                unverified_cnt += 1

            self.tree.insert("", tk.END, values=(o.order_number, o.patient.full_name, o.order_date.strftime("%Y-%m-%d %H:%M"), o.status, f"{o.total_amount:.2f}"))

        self.lbl_patients.config(text=str(len(today_patients)))
        self.lbl_orders.config(text=str(today_orders_cnt))
        self.lbl_pending.config(text=str(pending_cnt))
        self.lbl_unverified.config(text=str(unverified_cnt))


class PatientView(BaseView):
    def __init__(self, parent, session: Session):
        super().__init__(parent, session)
        self.patient_svc = PatientService(session)
        self._build_ui()

    def _build_ui(self):
        lbl = ttk.Label(self, text="Patient Management", font=("Helvetica", 16, "bold"))
        lbl.pack(anchor=tk.W, pady=10, padx=10)

        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(toolbar, text="Search (ID/Name/Phone):").pack(side=tk.LEFT, padx=(0, 5))
        self.ent_search = ttk.Entry(toolbar, width=25)
        self.ent_search.pack(side=tk.LEFT, padx=(0, 5))
        self.ent_search.bind("<KeyRelease>", lambda e: self.refresh())

        btn_new = ttk.Button(toolbar, text="+ New Patient", command=self._open_patient_form)
        btn_new.pack(side=tk.RIGHT, padx=5)

        # Table
        cols = ("id", "patient_id", "name", "gender", "age", "phone", "reg_date")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("patient_id", text="Patient ID")
        self.tree.heading("name", text="Full Name")
        self.tree.heading("gender", text="Gender")
        self.tree.heading("age", text="Age")
        self.tree.heading("phone", text="Phone")
        self.tree.heading("reg_date", text="Reg Date")

        self.tree.column("id", width=40)
        self.tree.column("patient_id", width=100)
        self.tree.column("name", width=180)
        self.tree.column("gender", width=80)
        self.tree.column("age", width=80)
        self.tree.column("phone", width=120)
        self.tree.column("reg_date", width=140)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def refresh(self):
        q = self.ent_search.get().strip()
        patients = self.patient_svc.search_patients(query=q)

        for item in self.tree.get_children():
            self.tree.delete(item)

        for p in patients:
            age_str = f"{p.age or ''} {p.age_unit or ''}".strip()
            self.tree.insert("", tk.END, values=(p.id, p.patient_id, p.full_name, p.gender, age_str, p.phone or "N/A", p.registration_date.strftime("%Y-%m-%d")))

    def _open_patient_form(self):
        dlg = tk.Toplevel(self)
        dlg.title("New Patient Registration")
        dlg.geometry("400x420")
        dlg.grab_set()

        f = ttk.Frame(dlg, padding=15)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text="Full Name:").grid(row=0, column=0, sticky=tk.W, pady=4)
        ent_name = ttk.Entry(f, width=28)
        ent_name.grid(row=0, column=1, sticky=tk.W, pady=4)

        ttk.Label(f, text="Gender:").grid(row=1, column=0, sticky=tk.W, pady=4)
        cb_gender = ttk.Combobox(f, values=["Male", "Female", "Other"], state="readonly", width=25)
        cb_gender.set("Male")
        cb_gender.grid(row=1, column=1, sticky=tk.W, pady=4)

        ttk.Label(f, text="Age:").grid(row=2, column=0, sticky=tk.W, pady=4)
        ent_age = ttk.Entry(f, width=28)
        ent_age.grid(row=2, column=1, sticky=tk.W, pady=4)

        ttk.Label(f, text="Phone:").grid(row=3, column=0, sticky=tk.W, pady=4)
        ent_phone = ttk.Entry(f, width=28)
        ent_phone.grid(row=3, column=1, sticky=tk.W, pady=4)

        ttk.Label(f, text="Address:").grid(row=4, column=0, sticky=tk.W, pady=4)
        ent_addr = ttk.Entry(f, width=28)
        ent_addr.grid(row=4, column=1, sticky=tk.W, pady=4)

        def save():
            name = ent_name.get().strip()
            if not name:
                messagebox.showerror("Error", "Name is required.", parent=dlg)
                return
            try:
                age_val = int(ent_age.get().strip()) if ent_age.get().strip() else None
                self.patient_svc.register_patient(
                    full_name=name,
                    gender=cb_gender.get(),
                    age=age_val,
                    phone=ent_phone.get().strip(),
                    address=ent_addr.get().strip()
                )
                messagebox.showinfo("Success", "Patient registered successfully!", parent=dlg)
                dlg.destroy()
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dlg)

        btn_save = ttk.Button(f, text="Save Patient", command=save)
        btn_save.grid(row=5, column=1, sticky=tk.E, pady=15)


class OrderView(BaseView):
    def __init__(self, parent, session: Session):
        super().__init__(parent, session)
        self.order_svc = OrderService(session)
        self.patient_svc = PatientService(session)
        self.test_svc = TestService(session)
        self.billing_svc = BillingService(session)
        self._build_ui()

    def _build_ui(self):
        lbl = ttk.Label(self, text="Lab Orders", font=("Helvetica", 16, "bold"))
        lbl.pack(anchor=tk.W, pady=10, padx=10)

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=10, pady=5)

        btn_new = ttk.Button(toolbar, text="+ Create New Order", command=self._open_order_form)
        btn_new.pack(side=tk.LEFT, padx=5)

        btn_collect = ttk.Button(toolbar, text="Sample Collection", command=self._open_sample_dialog)
        btn_collect.pack(side=tk.LEFT, padx=5)

        btn_pay = ttk.Button(toolbar, text="Record Payment", command=self._open_payment_dialog)
        btn_pay.pack(side=tk.LEFT, padx=5)

        # Table
        cols = ("id", "order_num", "patient_name", "date", "status", "total", "paid", "payment_status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("order_num", text="Order #")
        self.tree.heading("patient_name", text="Patient Name")
        self.tree.heading("date", text="Order Date")
        self.tree.heading("status", text="Order Status")
        self.tree.heading("total", text="Total (INR)")
        self.tree.heading("paid", text="Paid (INR)")
        self.tree.heading("payment_status", text="Payment Status")

        self.tree.column("id", width=40)
        self.tree.column("order_num", width=100)
        self.tree.column("patient_name", width=180)
        self.tree.column("date", width=140)
        self.tree.column("status", width=120)
        self.tree.column("total", width=90)
        self.tree.column("paid", width=90)
        self.tree.column("payment_status", width=110)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def refresh(self):
        order_repo = OrderRepository(self.session)
        orders = order_repo.search_orders(limit=100)

        for item in self.tree.get_children():
            self.tree.delete(item)

        for o in orders:
            self.tree.insert("", tk.END, values=(o.id, o.order_number, o.patient.full_name, o.order_date.strftime("%Y-%m-%d %H:%M"), o.status, f"{o.total_amount:.2f}", f"{o.paid_amount:.2f}", o.payment_status))

    def _open_order_form(self):
        dlg = tk.Toplevel(self)
        dlg.title("Create New Lab Order")
        dlg.geometry("500x500")
        dlg.grab_set()

        f = ttk.Frame(dlg, padding=15)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text="Select Patient:").grid(row=0, column=0, sticky=tk.W, pady=4)
        patients = self.patient_svc.search_patients()
        pat_map = {f"{p.patient_id} - {p.full_name}": p.id for p in patients}
        cb_pat = ttk.Combobox(f, values=list(pat_map.keys()), state="readonly", width=35)
        if pat_map:
            cb_pat.current(0)
        cb_pat.grid(row=0, column=1, sticky=tk.W, pady=4)

        ttk.Label(f, text="Select Tests:").grid(row=1, column=0, sticky=tk.NW, pady=4)
        lb_tests = tk.Listbox(f, selectmode=tk.MULTIPLE, height=10, width=35)
        lb_tests.grid(row=1, column=1, sticky=tk.W, pady=4)

        tests = self.test_svc.test_repo.get_all_tests(active_only=True)
        test_map = {}
        for idx, t in enumerate(tests):
            lb_tests.insert(tk.END, f"{t.code} - {t.name} (INR {t.price:.2f})")
            test_map[idx] = t.id

        ttk.Label(f, text="Discount (INR):").grid(row=2, column=0, sticky=tk.W, pady=4)
        ent_disc = ttk.Entry(f, width=35)
        ent_disc.insert(0, "0.0")
        ent_disc.grid(row=2, column=1, sticky=tk.W, pady=4)

        def save():
            pat_sel = cb_pat.get()
            if not pat_sel or pat_sel not in pat_map:
                messagebox.showerror("Error", "Please select a valid patient.", parent=dlg)
                return
            selected_indices = lb_tests.curselection()
            if not selected_indices:
                messagebox.showerror("Error", "Please select at least one test.", parent=dlg)
                return

            p_id = pat_map[pat_sel]
            t_ids = [test_map[i] for i in selected_indices]
            try:
                disc = float(ent_disc.get().strip() or "0.0")
                order = self.order_svc.create_order(p_id, t_ids, discount_amount=disc)
                messagebox.showinfo("Success", f"Order {order.order_number} created successfully!", parent=dlg)
                dlg.destroy()
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dlg)

        btn_save = ttk.Button(f, text="Create Order", command=save)
        btn_save.grid(row=3, column=1, sticky=tk.E, pady=15)

    def _open_sample_dialog(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Please select an order from the list first.")
            return

        order_id = self.tree.item(sel[0])['values'][0]
        order = self.order_svc.order_repo.get_by_id(order_id)

        dlg = tk.Toplevel(self)
        dlg.title(f"Sample Collection - Order {order.order_number}")
        dlg.geometry("450x300")
        dlg.grab_set()

        f = ttk.Frame(dlg, padding=15)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text=f"Order: {order.order_number} ({order.patient.full_name})", font=("Helvetica", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))

        for sc in order.samples:
            sf = ttk.Frame(f)
            sf.pack(fill=tk.X, pady=5)
            ttk.Label(sf, text=f"Sample: {sc.sample_type} - {'Collected' if sc.is_collected else 'Pending'}").pack(side=tk.LEFT)
            if not sc.is_collected:
                def do_collect(sc_id=sc.id):
                    self.order_svc.record_sample_collection(order.id, sc_id, sample_identifier="BAR123")
                    messagebox.showinfo("Success", "Sample marked as collected!", parent=dlg)
                    dlg.destroy()
                    self.refresh()
                btn = ttk.Button(sf, text="Mark Collected", command=do_collect)
                btn.pack(side=tk.RIGHT)

    def _open_payment_dialog(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Please select an order from the list first.")
            return

        order_id = self.tree.item(sel[0])['values'][0]
        order = self.order_svc.order_repo.get_by_id(order_id)

        dlg = tk.Toplevel(self)
        dlg.title(f"Record Payment - Order {order.order_number}")
        dlg.geometry("380x280")
        dlg.grab_set()

        f = ttk.Frame(dlg, padding=15)
        f.pack(fill=tk.BOTH, expand=True)

        bal = max(0.0, order.total_amount - order.paid_amount)
        ttk.Label(f, text=f"Total: INR {order.total_amount:.2f} | Paid: INR {order.paid_amount:.2f}", font=("Helvetica", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(f, text=f"Balance Remaining: INR {bal:.2f}", font=("Helvetica", 10, "bold"), foreground="#CC0000").pack(anchor=tk.W, pady=(0, 15))

        ttk.Label(f, text="Payment Amount (INR):").pack(anchor=tk.W)
        ent_amt = ttk.Entry(f, width=30)
        ent_amt.insert(0, f"{bal:.2f}")
        ent_amt.pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(f, text="Payment Method:").pack(anchor=tk.W)
        cb_method = ttk.Combobox(f, values=["Cash", "UPI", "Card", "Other"], state="readonly", width=27)
        cb_method.set("Cash")
        cb_method.pack(anchor=tk.W, pady=(0, 15))

        def pay():
            try:
                amt = float(ent_amt.get().strip())
                pm = cb_method.get()
                p = self.billing_svc.record_payment(order.id, amt, pm)
                messagebox.showinfo("Success", f"Payment recorded! Receipt: {p.receipt_number}", parent=dlg)
                dlg.destroy()
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dlg)

        btn_pay = ttk.Button(f, text="Record Payment", command=pay)
        btn_pay.pack(anchor=tk.E)


class ResultView(BaseView):
    def __init__(self, parent, session: Session):
        super().__init__(parent, session)
        self.order_svc = OrderService(session)
        self.result_svc = ResultService(session)
        self.verify_svc = VerificationService(session)
        self._build_ui()

    def _build_ui(self):
        lbl = ttk.Label(self, text="Result Entry & Verification", font=("Helvetica", 16, "bold"))
        lbl.pack(anchor=tk.W, pady=10, padx=10)

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=10, pady=5)

        btn_enter = ttk.Button(toolbar, text="Enter Results", command=self._open_result_entry)
        btn_enter.pack(side=tk.LEFT, padx=5)

        btn_verify = ttk.Button(toolbar, text="Verify Results", command=self._verify_selected)
        btn_verify.pack(side=tk.LEFT, padx=5)

        cols = ("id", "order_num", "patient_name", "date", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("order_num", text="Order #")
        self.tree.heading("patient_name", text="Patient Name")
        self.tree.heading("date", text="Order Date")
        self.tree.heading("status", text="Order Status")

        self.tree.column("id", width=40)
        self.tree.column("order_num", width=120)
        self.tree.column("patient_name", width=220)
        self.tree.column("date", width=160)
        self.tree.column("status", width=150)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def refresh(self):
        order_repo = OrderRepository(self.session)
        orders = order_repo.search_orders(limit=100)

        for item in self.tree.get_children():
            self.tree.delete(item)

        for o in orders:
            self.tree.insert("", tk.END, values=(o.id, o.order_number, o.patient.full_name, o.order_date.strftime("%Y-%m-%d %H:%M"), o.status))

    def _open_result_entry(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Please select an order first.")
            return

        order_id = self.tree.item(sel[0])['values'][0]
        order = self.order_svc.order_repo.get_by_id(order_id)

        dlg = tk.Toplevel(self)
        dlg.title(f"Result Entry - Order {order.order_number}")
        dlg.geometry("550x450")
        dlg.grab_set()

        f = ttk.Frame(dlg, padding=15)
        f.pack(fill=tk.BOTH, expand=True)

        entries = {}
        row_idx = 0

        for item in order.items:
            ttk.Label(f, text=f"Test: {item.test_name_snapshot}", font=("Helvetica", 10, "bold")).grid(row=row_idx, column=0, columnspan=3, sticky=tk.W, pady=(8, 4))
            row_idx += 1

            for res in item.results:
                ttk.Label(f, text=f"{res.parameter_name_snapshot}:").grid(row=row_idx, column=0, sticky=tk.W, pady=2)
                ent = ttk.Entry(f, width=15)
                if res.result_value:
                    ent.insert(0, res.result_value)
                ent.grid(row=row_idx, column=1, sticky=tk.W, pady=2)
                ttk.Label(f, text=f"{res.unit_snapshot or ''} (Ref: {res.reference_range_snapshot or 'N/A'})").grid(row=row_idx, column=2, sticky=tk.W, pady=2, padx=5)

                entries[res.id] = ent
                row_idx += 1

        def save():
            results_map = {res_id: ent.get().strip() for res_id, ent in entries.items()}
            try:
                self.result_svc.save_results(order.id, results_map)
                messagebox.showinfo("Success", "Results saved successfully!", parent=dlg)
                dlg.destroy()
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dlg)

        btn_save = ttk.Button(f, text="Save Results", command=save)
        btn_save.grid(row=row_idx, column=2, sticky=tk.E, pady=15)

    def _verify_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Please select an order first.")
            return

        order_id = self.tree.item(sel[0])['values'][0]
        try:
            self.verify_svc.verify_order_results(order_id)
            messagebox.showinfo("Success", "Order results verified successfully!")
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e))


class ReportView(BaseView):
    def __init__(self, parent, session: Session):
        super().__init__(parent, session)
        self.report_svc = ReportService(session)
        self.order_svc = OrderService(session)
        self._build_ui()

    def _build_ui(self):
        lbl = ttk.Label(self, text="Report & Receipt Generation", font=("Helvetica", 16, "bold"))
        lbl.pack(anchor=tk.W, pady=10, padx=10)

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=10, pady=5)

        btn_gen_rpt = ttk.Button(toolbar, text="Generate Lab Report PDF", command=self._generate_report)
        btn_gen_rpt.pack(side=tk.LEFT, padx=5)

        cols = ("id", "order_num", "patient_name", "date", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("order_num", text="Order #")
        self.tree.heading("patient_name", text="Patient Name")
        self.tree.heading("date", text="Order Date")
        self.tree.heading("status", text="Order Status")

        self.tree.column("id", width=40)
        self.tree.column("order_num", width=120)
        self.tree.column("patient_name", width=220)
        self.tree.column("date", width=160)
        self.tree.column("status", width=150)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def refresh(self):
        order_repo = OrderRepository(self.session)
        orders = order_repo.search_orders(limit=100)

        for item in self.tree.get_children():
            self.tree.delete(item)

        for o in orders:
            self.tree.insert("", tk.END, values=(o.id, o.order_number, o.patient.full_name, o.order_date.strftime("%Y-%m-%d %H:%M"), o.status))

    def _generate_report(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Please select an order from the list.")
            return

        order_id = self.tree.item(sel[0])['values'][0]
        order = self.order_svc.order_repo.get_by_id(order_id)

        try:
            pdf_path = self.report_svc.generate_patient_report(order)
            messagebox.showinfo("Report Generated", f"Report generated successfully!\nPath: {pdf_path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))


class TestCatalogView(BaseView):
    def __init__(self, parent, session: Session):
        super().__init__(parent, session)
        self.test_svc = TestService(session)
        self._build_ui()

    def _build_ui(self):
        lbl = ttk.Label(self, text="Test Catalog & Parameters", font=("Helvetica", 16, "bold"))
        lbl.pack(anchor=tk.W, pady=10, padx=10)

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=10, pady=5)

        btn_new_test = ttk.Button(toolbar, text="+ Add New Test", command=self._open_test_form)
        btn_new_test.pack(side=tk.LEFT, padx=5)

        cols = ("id", "code", "name", "sample_type", "price", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("code", text="Test Code")
        self.tree.heading("name", text="Test Name")
        self.tree.heading("sample_type", text="Sample Type")
        self.tree.heading("price", text="Price (INR)")
        self.tree.heading("status", text="Status")

        self.tree.column("id", width=40)
        self.tree.column("code", width=100)
        self.tree.column("name", width=220)
        self.tree.column("sample_type", width=120)
        self.tree.column("price", width=100)
        self.tree.column("status", width=100)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def refresh(self):
        tests = self.test_svc.test_repo.get_all_tests()

        for item in self.tree.get_children():
            self.tree.delete(item)

        for t in tests:
            self.tree.insert("", tk.END, values=(t.id, t.code, t.name, t.sample_type or "Blood", f"{t.price:.2f}", "Active" if t.is_active else "Inactive"))

    def _open_test_form(self):
        dlg = tk.Toplevel(self)
        dlg.title("Add New Test")
        dlg.geometry("420x380")
        dlg.grab_set()

        f = ttk.Frame(dlg, padding=15)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text="Test Code (e.g. CBC):").grid(row=0, column=0, sticky=tk.W, pady=4)
        ent_code = ttk.Entry(f, width=28)
        ent_code.grid(row=0, column=1, sticky=tk.W, pady=4)

        ttk.Label(f, text="Test Name:").grid(row=1, column=0, sticky=tk.W, pady=4)
        ent_name = ttk.Entry(f, width=28)
        ent_name.grid(row=1, column=1, sticky=tk.W, pady=4)

        ttk.Label(f, text="Sample Type:").grid(row=2, column=0, sticky=tk.W, pady=4)
        ent_sample = ttk.Entry(f, width=28)
        ent_sample.insert(0, "Blood")
        ent_sample.grid(row=2, column=1, sticky=tk.W, pady=4)

        ttk.Label(f, text="Price (INR):").grid(row=3, column=0, sticky=tk.W, pady=4)
        ent_price = ttk.Entry(f, width=28)
        ent_price.insert(0, "0.0")
        ent_price.grid(row=3, column=1, sticky=tk.W, pady=4)

        def save():
            code = ent_code.get().strip()
            name = ent_name.get().strip()
            if not code or not name:
                messagebox.showerror("Error", "Code and Name are required.", parent=dlg)
                return
            try:
                price = float(ent_price.get().strip() or "0.0")
                test = self.test_svc.create_test(code, name, price, sample_type=ent_sample.get().strip())
                # Add default single parameter if none
                p = self.test_svc.add_parameter(test.id, code, name)
                self.test_svc.add_reference_range(p.id, text_range="Normal")

                messagebox.showinfo("Success", "Test added successfully!", parent=dlg)
                dlg.destroy()
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dlg)

        btn_save = ttk.Button(f, text="Save Test", command=save)
        btn_save.grid(row=4, column=1, sticky=tk.E, pady=15)


class UserManagementView(BaseView):
    def __init__(self, parent, session: Session):
        super().__init__(parent, session)
        self._build_ui()

    def _build_ui(self):
        lbl = ttk.Label(self, text="User & Role Management", font=("Helvetica", 16, "bold"))
        lbl.pack(anchor=tk.W, pady=10, padx=10)

        cols = ("id", "username", "display_name", "roles", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("username", text="Username")
        self.tree.heading("display_name", text="Display Name")
        self.tree.heading("roles", text="Roles")
        self.tree.heading("status", text="Status")

        self.tree.column("id", width=40)
        self.tree.column("username", width=120)
        self.tree.column("display_name", width=180)
        self.tree.column("roles", width=200)
        self.tree.column("status", width=100)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def refresh(self):
        users = self.session.query(User).all()

        for item in self.tree.get_children():
            self.tree.delete(item)

        for u in users:
            r_str = ", ".join([r.name for r in u.roles])
            self.tree.insert("", tk.END, values=(u.id, u.username, u.display_name, r_str, "Active" if u.is_active else "Inactive"))


class AuditLogView(BaseView):
    def __init__(self, parent, session: Session):
        super().__init__(parent, session)
        self.audit_repo = AuditRepository(session)
        self._build_ui()

    def _build_ui(self):
        lbl = ttk.Label(self, text="System Audit Log", font=("Helvetica", 16, "bold"))
        lbl.pack(anchor=tk.W, pady=10, padx=10)

        cols = ("timestamp", "user", "action", "entity", "details")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        self.tree.heading("timestamp", text="Timestamp")
        self.tree.heading("user", text="User")
        self.tree.heading("action", text="Action")
        self.tree.heading("entity", text="Entity")
        self.tree.heading("details", text="Details")

        self.tree.column("timestamp", width=140)
        self.tree.column("user", width=100)
        self.tree.column("action", width=150)
        self.tree.column("entity", width=100)
        self.tree.column("details", width=250)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def refresh(self):
        logs = self.audit_repo.get_logs(limit=100)

        for item in self.tree.get_children():
            self.tree.delete(item)

        for log in logs:
            self.tree.insert("", tk.END, values=(log.timestamp.strftime("%Y-%m-%d %H:%M:%S"), log.username, log.action, log.entity or "", log.details or ""))


class BackupRestoreView(BaseView):
    def __init__(self, parent, session: Session):
        super().__init__(parent, session)
        self.backup_svc = BackupService(session)
        self._build_ui()

    def _build_ui(self):
        lbl = ttk.Label(self, text="Database Backup & Restore", font=("Helvetica", 16, "bold"))
        lbl.pack(anchor=tk.W, pady=10, padx=10)

        f = ttk.LabelFrame(self, text=" Database Operations ", padding=15)
        f.pack(fill=tk.X, padx=10, pady=10)

        btn_backup = ttk.Button(f, text="Create Manual Backup", command=self._create_backup)
        btn_backup.pack(anchor=tk.W, pady=5)

        btn_restore = ttk.Button(f, text="Restore Database from Backup File", command=self._restore_backup)
        btn_restore.pack(anchor=tk.W, pady=5)

    def _create_backup(self):
        try:
            path = self.backup_svc.create_backup()
            messagebox.showinfo("Backup Success", f"Database backup created successfully!\nPath: {path}")
        except Exception as e:
            messagebox.showerror("Backup Error", str(e))

    def _restore_backup(self):
        filepath = filedialog.askopenfilename(
            title="Select Backup File",
            filetypes=[("SQLite Database Files", "*.db")]
        )
        if not filepath:
            return

        if messagebox.askyesno("Confirm Restore", "Are you sure you want to restore the database from this backup?\n\nA safety backup of current data will be created automatically before restore."):
            try:
                self.backup_svc.restore_backup(filepath)
                messagebox.showinfo("Restore Success", "Database restored successfully!")
            except Exception as e:
                messagebox.showerror("Restore Error", str(e))


class SettingsView(BaseView):
    def __init__(self, parent, session: Session):
        super().__init__(parent, session)
        self.setting_repo = SettingRepository(session)
        self._build_ui()

    def _build_ui(self):
        lbl = ttk.Label(self, text="Laboratory Settings", font=("Helvetica", 16, "bold"))
        lbl.pack(anchor=tk.W, pady=10, padx=10)

        f = ttk.LabelFrame(self, text=" Laboratory Details ", padding=15)
        f.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(f, text="Lab Name:").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.ent_name = ttk.Entry(f, width=40)
        self.ent_name.grid(row=0, column=1, sticky=tk.W, pady=4)

        ttk.Label(f, text="Address:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.ent_addr = ttk.Entry(f, width=40)
        self.ent_addr.grid(row=1, column=1, sticky=tk.W, pady=4)

        ttk.Label(f, text="Phone:").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.ent_phone = ttk.Entry(f, width=40)
        self.ent_phone.grid(row=2, column=1, sticky=tk.W, pady=4)

        btn_save = ttk.Button(f, text="Save Settings", command=self._save_settings)
        btn_save.grid(row=3, column=1, sticky=tk.E, pady=10)

    def refresh(self):
        self.ent_name.delete(0, tk.END)
        self.ent_name.insert(0, self.setting_repo.get("lab_name", ""))

        self.ent_addr.delete(0, tk.END)
        self.ent_addr.insert(0, self.setting_repo.get("lab_address", ""))

        self.ent_phone.delete(0, tk.END)
        self.ent_phone.insert(0, self.setting_repo.get("lab_phone", ""))

    def _save_settings(self):
        self.setting_repo.set("lab_name", self.ent_name.get().strip())
        self.setting_repo.set("lab_address", self.ent_addr.get().strip())
        self.setting_repo.set("lab_phone", self.ent_phone.get().strip())
        messagebox.showinfo("Success", "Settings saved successfully!")
