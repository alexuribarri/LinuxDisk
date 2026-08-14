import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
from typing import Dict, Any, List, Optional
from ..core.disk_scanner import DiskScanner
from ..core.benchmark_engine import BenchmarkEngine
from ..core.exporter import ListingExporter

class LinuxDiskGUI:
    """Modern Dark-Themed CrystalDisk GUI for Ubuntu / Linux Desktop."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("LinuxDisk — CrystalDisk Suite for Linux")
        self.root.geometry("980x700")
        self.root.minsize(880, 600)
        self.root.configure(bg="#1e1e24")

        self.scanner = DiskScanner()
        self.bench_engine = BenchmarkEngine()
        self.disks: List[Dict[str, Any]] = []
        self.selected_disk: Optional[Dict[str, Any]] = None
        self.benchmark_results: Dict[str, Any] = {}
        self.is_benchmarking = False

        self._setup_styles()
        self._build_layout()
        self.refresh_disks()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Dark theme palette
        self.bg_dark = "#18181c"
        self.bg_card = "#24242c"
        self.bg_highlight = "#2e2e38"
        self.fg_primary = "#ffffff"
        self.fg_secondary = "#a0a0b0"
        self.accent_blue = "#3b82f6"
        self.accent_green = "#10b981"
        self.accent_teal = "#14b8a6"
        self.accent_red = "#ef4444"

        style.configure("TFrame", background=self.bg_dark)
        style.configure("Card.TFrame", background=self.bg_card, relief="flat")
        style.configure("TNotebook", background=self.bg_dark, borderwidth=0)
        style.configure("TNotebook.Tab", background=self.bg_card, foreground=self.fg_secondary, padding=[16, 8], font=("Helvetica", 11, "bold"))
        style.map("TNotebook.Tab", background=[("selected", self.accent_blue)], foreground=[("selected", "#ffffff")])

        style.configure("Treeview", background=self.bg_card, foreground=self.fg_primary, fieldbackground=self.bg_card, rowheight=24, font=("Helvetica", 10))
        style.configure("Treeview.Heading", background=self.bg_highlight, foreground=self.fg_primary, font=("Helvetica", 10, "bold"))
        style.map("Treeview", background=[("selected", self.accent_blue)], foreground=[("selected", "#ffffff")])

    def _build_layout(self):
        # Top Header Bar
        header = tk.Frame(self.root, bg=self.bg_dark, height=45)
        header.pack(fill="x", padx=16, pady=8)

        lbl_title = tk.Label(header, text="💾 LinuxDisk", font=("Helvetica", 16, "bold"), fg=self.fg_primary, bg=self.bg_dark)
        lbl_title.pack(side="left")

        is_root = os.geteuid() == 0 if hasattr(os, "geteuid") else False
        perm_text = "🔒 Sudo Mode (Full Access)" if is_root else "⚠️ Standard User (Run with sudo for full SMART)"
        perm_color = self.accent_green if is_root else "#eab308"
        lbl_perm = tk.Label(header, text=perm_text, font=("Helvetica", 9, "bold"), fg=perm_color, bg=self.bg_dark)
        lbl_perm.pack(side="left", padx=12, pady=4)

        btn_rescan = tk.Button(header, text="🔄 Rescan Disks", command=self.refresh_disks, bg=self.bg_card, fg=self.fg_primary, relief="flat", padx=10, pady=4, cursor="hand2")
        btn_rescan.pack(side="right")

        # Main Body Splitter (Sidebar + Detail)
        body = tk.Frame(self.root, bg=self.bg_dark)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # Left Sidebar (Disks List)
        sidebar = tk.Frame(body, bg=self.bg_card, width=240)
        sidebar.pack(side="left", fill="y", padx=(0, 12))
        sidebar.pack_propagate(False)

        lbl_disks = tk.Label(sidebar, text="PHYSICAL DISKS", font=("Helvetica", 9, "bold"), fg=self.fg_secondary, bg=self.bg_card)
        lbl_disks.pack(anchor="w", padx=12, pady=(12, 6))

        self.disk_listbox = tk.Listbox(sidebar, bg=self.bg_card, fg=self.fg_primary, selectbackground=self.accent_blue, selectforeground="#ffffff", borderwidth=0, highlightthickness=0, font=("Helvetica", 10))
        self.disk_listbox.pack(fill="both", expand=True, padx=8, pady=4)
        self.disk_listbox.bind("<<ListboxSelect>>", self._on_disk_selected)

        # Right Detail Notebook (Tabs)
        self.notebook = ttk.Notebook(body)
        self.notebook.pack(side="right", fill="both", expand=True)

        self.tab_health = tk.Frame(self.notebook, bg=self.bg_dark)
        self.tab_bench = tk.Frame(self.notebook, bg=self.bg_dark)
        self.tab_proof = tk.Frame(self.notebook, bg=self.bg_dark)

        self.notebook.add(self.tab_health, text="🩺 Health & S.M.A.R.T.")
        self.notebook.add(self.tab_bench, text="⚡ Speed Benchmark")
        self.notebook.add(self.tab_proof, text="📦 Selling Proof")

        self._build_health_tab()
        self._build_benchmark_tab()
        self._build_proof_tab()

    def _build_health_tab(self):
        # Top Diagnostic Card
        top_card = tk.Frame(self.tab_health, bg=self.bg_card, padx=16, pady=16)
        top_card.pack(fill="x", padx=8, pady=8)

        # Health Shield Badge
        self.lbl_health_badge = tk.Label(top_card, text="GOOD\n100%", font=("Helvetica", 14, "bold"), fg=self.accent_green, bg="#0d281e", padx=16, pady=12)
        self.lbl_health_badge.pack(side="left", padx=(0, 16))

        # Drive Info Grid
        info_frame = tk.Frame(top_card, bg=self.bg_card)
        info_frame.pack(side="left", fill="both", expand=True)

        self.lbl_model = tk.Label(info_frame, text="Select a drive...", font=("Helvetica", 14, "bold"), fg=self.fg_primary, bg=self.bg_card)
        self.lbl_model.pack(anchor="w")

        self.lbl_specs = tk.Label(info_frame, text="Capacity: -- | Interface: -- | Speed: --", font=("Helvetica", 10), fg=self.fg_secondary, bg=self.bg_card)
        self.lbl_specs.pack(anchor="w", pady=(2, 6))

        self.lbl_runtime = tk.Label(info_frame, text="Power-On Hours: -- | Power Cycles: -- | Temp: --", font=("Helvetica", 10, "bold"), fg=self.fg_primary, bg=self.bg_card)
        self.lbl_runtime.pack(anchor="w")

        # Critical HDD Health Indicators (ID 05, C5, C6)
        crit_frame = tk.Frame(self.tab_health, bg=self.bg_dark)
        crit_frame.pack(fill="x", padx=8, pady=4)

        self.card_realloc = self._create_crit_card(crit_frame, "Reallocated Bad Sectors (05)", "0 Bad Sectors")
        self.card_pending = self._create_crit_card(crit_frame, "Pending Sectors (C5)", "0 Pending")
        self.card_uncorr = self._create_crit_card(crit_frame, "Uncorrectable Errors (C6)", "0 Errors")

        # S.M.A.R.T. Attribute Table
        lbl_table = tk.Label(self.tab_health, text="S.M.A.R.T. ATTRIBUTES TABLE", font=("Helvetica", 9, "bold"), fg=self.fg_secondary, bg=self.bg_dark)
        lbl_table.pack(anchor="w", padx=8, pady=(8, 4))

        columns = ("id", "name", "current", "worst", "thresh", "raw", "status")
        self.tree_smart = ttk.Treeview(self.tab_health, columns=columns, show="headings", height=10)
        self.tree_smart.heading("id", text="ID")
        self.tree_smart.heading("name", text="Attribute Name")
        self.tree_smart.heading("current", text="Current")
        self.tree_smart.heading("worst", text="Worst")
        self.tree_smart.heading("thresh", text="Threshold")
        self.tree_smart.heading("raw", text="Raw Value")
        self.tree_smart.heading("status", text="Status")

        self.tree_smart.column("id", width=45, anchor="center")
        self.tree_smart.column("name", width=220)
        self.tree_smart.column("current", width=65, anchor="center")
        self.tree_smart.column("worst", width=65, anchor="center")
        self.tree_smart.column("thresh", width=70, anchor="center")
        self.tree_smart.column("raw", width=120, anchor="center")
        self.tree_smart.column("status", width=80, anchor="center")

        self.tree_smart.pack(fill="both", expand=True, padx=8, pady=4)

    def _create_crit_card(self, parent: tk.Frame, title: str, default_text: str) -> tk.Label:
        box = tk.Frame(parent, bg=self.bg_card, padx=12, pady=8)
        box.pack(side="left", fill="x", expand=True, padx=4)

        t_lbl = tk.Label(box, text=title, font=("Helvetica", 9), fg=self.fg_secondary, bg=self.bg_card)
        t_lbl.pack(anchor="w")

        v_lbl = tk.Label(box, text=default_text, font=("Helvetica", 11, "bold"), fg=self.accent_green, bg=self.bg_card)
        v_lbl.pack(anchor="w", pady=(2, 0))
        return v_lbl

    def _build_benchmark_tab(self):
        ctrl_bar = tk.Frame(self.tab_bench, bg=self.bg_card, padx=12, pady=10)
        ctrl_bar.pack(fill="x", padx=8, pady=8)

        self.btn_run_bench = tk.Button(ctrl_bar, text="▶ ALL", font=("Helvetica", 11, "bold"), bg=self.accent_teal, fg="#ffffff", padx=16, pady=4, relief="flat", cursor="hand2", command=self._toggle_benchmark)
        self.btn_run_bench.pack(side="left", padx=(0, 16))

        tk.Label(ctrl_bar, text="Size:", font=("Helvetica", 10), fg=self.fg_secondary, bg=self.bg_card).pack(side="left")
        self.bench_size_var = tk.StringVar(value="256")
        cmb_size = ttk.Combobox(ctrl_bar, textvariable=self.bench_size_var, values=["64", "128", "256", "512"], width=5, state="readonly")
        cmb_size.pack(side="left", padx=(4, 12))

        tk.Label(ctrl_bar, text="Target:", font=("Helvetica", 10), fg=self.fg_secondary, bg=self.bg_card).pack(side="left")
        self.target_dir_var = tk.StringVar(value="/tmp")
        self.cmb_target = ttk.Combobox(ctrl_bar, textvariable=self.target_dir_var, values=["/tmp", os.path.expanduser("~")], width=18)
        self.cmb_target.pack(side="left", padx=(4, 4))

        btn_browse = tk.Button(ctrl_bar, text="Browse...", font=("Helvetica", 9), bg=self.bg_highlight, fg=self.fg_primary, padx=6, pady=2, relief="flat", command=self._browse_target_folder)
        btn_browse.pack(side="left", padx=(0, 12))

        self.lbl_bench_status = tk.Label(ctrl_bar, text="Ready", font=("Helvetica", 10), fg=self.fg_secondary, bg=self.bg_card)
        self.lbl_bench_status.pack(side="left", padx=4)

        # Progress bar
        self.progress_bench = ttk.Progressbar(self.tab_bench, orient="horizontal", mode="determinate")
        self.progress_bench.pack(fill="x", padx=8, pady=4)

        # Benchmark Matrix Frame (CrystalDiskMark Layout)
        matrix = tk.Frame(self.tab_bench, bg=self.bg_dark)
        matrix.pack(fill="both", expand=True, padx=8, pady=8)

        self.bench_score_widgets = {}
        for profile in BenchmarkEngine.TEST_PROFILES:
            pid = profile["id"]
            row_frame = tk.Frame(matrix, bg=self.bg_card, padx=12, pady=8)
            row_frame.pack(fill="x", pady=4)

            lbl_pname = tk.Label(row_frame, text=profile["name"], font=("Helvetica", 11, "bold"), fg=self.fg_primary, bg=self.bg_card, width=16, anchor="w")
            lbl_pname.pack(side="left")

            lbl_sub = tk.Label(row_frame, text=profile["sub"], font=("Helvetica", 9), fg=self.fg_secondary, bg=self.bg_card, width=24, anchor="w")
            lbl_sub.pack(side="left")

            # Read score box
            read_box = tk.Label(row_frame, text="-- MB/s", font=("Helvetica", 14, "bold"), fg=self.accent_teal, bg=self.bg_highlight, width=14, pady=6)
            read_box.pack(side="left", padx=8)

            # Write score box
            write_box = tk.Label(row_frame, text="-- MB/s", font=("Helvetica", 14, "bold"), fg=self.accent_blue, bg=self.bg_highlight, width=14, pady=6)
            write_box.pack(side="left", padx=8)

            self.bench_score_widgets[pid] = {"read": read_box, "write": write_box}

    def _browse_target_folder(self):
        d = filedialog.askdirectory(title="Select Target Folder to Benchmark")
        if d:
            self.target_dir_var.set(d)

    def _build_proof_tab(self):
        top_bar = tk.Frame(self.tab_proof, bg=self.bg_dark)
        top_bar.pack(fill="x", padx=8, pady=8)

        btn_copy = tk.Button(top_bar, text="📋 Copy Markdown for eBay/Reddit", font=("Helvetica", 10, "bold"), bg=self.accent_blue, fg="#ffffff", padx=12, pady=6, relief="flat", cursor="hand2", command=self._copy_markdown)
        btn_copy.pack(side="left")

        btn_save = tk.Button(top_bar, text="💾 Save Report (.md)", font=("Helvetica", 10), bg=self.bg_card, fg=self.fg_primary, padx=12, pady=6, relief="flat", cursor="hand2", command=self._save_report)
        btn_save.pack(side="left", padx=12)

        self.txt_proof = tk.Text(self.tab_proof, bg=self.bg_card, fg=self.fg_primary, insertbackground="#ffffff", borderwidth=0, padx=12, pady=12, font=("Courier", 10))
        self.txt_proof.pack(fill="both", expand=True, padx=8, pady=4)

    def refresh_disks(self):
        self.disks = self.scanner.scan_disks()
        self.disk_listbox.delete(0, tk.END)
        for d in self.disks:
            self.disk_listbox.insert(tk.END, f"{d['model']} ({d['size_formatted']})")
        if self.disks:
            self.disk_listbox.selection_set(0)
            self._display_disk(self.disks[0])

    def _on_disk_selected(self, event):
        sel = self.disk_listbox.curselection()
        if sel and sel[0] < len(self.disks):
            self._display_disk(self.disks[sel[0]])

    def _display_disk(self, disk: Dict[str, Any]):
        self.selected_disk = disk
        smart = disk.get("smart") or {}

        # Update available target directories
        import shutil
        mounts = disk.get("mounts", [])
        avail_targets = []
        for m in mounts:
            if os.path.exists(m) and os.access(m, os.W_OK):
                avail_targets.append(m)
        avail_targets.extend(["/tmp", os.path.expanduser("~")])
        avail_targets = list(dict.fromkeys(avail_targets))
        self.cmb_target["values"] = avail_targets

        # Select best initial target with sufficient free space
        best_target = "/tmp"
        for m in avail_targets:
            try:
                if shutil.disk_usage(m).free >= 64 * 1024 * 1024:
                    best_target = m
                    break
            except Exception:
                pass
        self.target_dir_var.set(best_target)

        # Top diagnostic card
        grade = smart.get("health_grade", "GOOD")
        score = smart.get("health_score", 100)
        self.lbl_health_badge.config(text=f"{grade}\n{score}%", fg=self.accent_green if grade == "GOOD" else (self.accent_red if grade == "BAD" else "#eab308"))

        self.lbl_model.config(text=disk.get("model", "Storage Device"))
        self.lbl_specs.config(text=f"Path: {disk['path']} | Serial: {disk.get('serial', 'N/A')} | Size: {disk['size_formatted']} | {disk['rotation']}")

        poh = smart.get("power_on_hours", "N/A")
        poh_str = f"{poh} hrs ({poh // 24} days)" if isinstance(poh, int) else "N/A"
        temp = smart.get("temperature")
        temp_str = f"{temp} °C / {int(temp * 9/5 + 32)} °F" if temp is not None else "-- °C"
        self.lbl_runtime.config(text=f"Power-On Time: {poh_str} | Cycles: {smart.get('power_cycles', 'N/A')} | Temp: {temp_str}")

        # Critical indicators
        realloc = smart.get("reallocated_sectors", 0)
        pending = smart.get("pending_sectors", 0)
        uncorr = smart.get("uncorrectable_sectors", 0)

        self.card_realloc.config(text=f"{realloc} Bad Sectors", fg=self.accent_green if realloc == 0 else self.accent_red)
        self.card_pending.config(text=f"{pending} Pending", fg=self.accent_green if pending == 0 else self.accent_red)
        self.card_uncorr.config(text=f"{uncorr} Errors", fg=self.accent_green if uncorr == 0 else self.accent_red)

        # Populate SMART Table
        for row in self.tree_smart.get_children():
            self.tree_smart.delete(row)

        for attr in smart.get("smart_attributes", []):
            self.tree_smart.insert("", tk.END, values=(
                attr["id_hex"],
                attr["name"],
                attr["current"],
                attr["worst"],
                attr["threshold"],
                attr["raw_formatted"],
                attr["status"]
            ))

        # Update Proof Markdown
        md = ListingExporter.generate_markdown(disk, self.benchmark_results)
        self.txt_proof.delete("1.0", tk.END)
        self.txt_proof.insert("1.0", md)

    def _toggle_benchmark(self):
        if self.is_benchmarking:
            self.bench_engine.stop()
            self.btn_run_bench.config(text="▶ ALL", bg=self.accent_teal)
            self.is_benchmarking = False
            return

        target_dir = self.target_dir_var.get().strip() or "/tmp"

        self.is_benchmarking = True
        self.btn_run_bench.config(text="⏹ STOP", bg=self.accent_red)
        self.progress_bench["value"] = 0

        def run_thread():
            size_mb = int(self.bench_size_var.get())
            def on_progress(msg, prog, results):
                self.root.after(0, lambda: self._update_bench_ui(msg, prog, results))

            try:
                res = self.bench_engine.run_benchmark(target_dir, size_mb, on_progress)
                self.benchmark_results = res
            except Exception as e:
                self.bench_engine.last_error = str(e)
            finally:
                self.root.after(0, self._finish_benchmark)

        threading.Thread(target=run_thread, daemon=True).start()

    def _update_bench_ui(self, msg: str, progress: float, results: Dict[str, Any]):
        self.lbl_bench_status.config(text=msg)
        self.progress_bench["value"] = progress * 100

        for pid, rdata in results.items():
            if pid in self.bench_score_widgets:
                w_read = self.bench_score_widgets[pid]["read"]
                w_write = self.bench_score_widgets[pid]["write"]

                if rdata.get("read_mbs") is not None:
                    w_read.config(text=f"{rdata['read_mbs']:.1f} MB/s")
                if rdata.get("write_mbs") is not None:
                    w_write.config(text=f"{rdata['write_mbs']:.1f} MB/s")

    def _finish_benchmark(self):
        self.is_benchmarking = False
        self.btn_run_bench.config(text="▶ ALL", bg=self.accent_teal)
        if self.selected_disk:
            md = ListingExporter.generate_markdown(self.selected_disk, self.benchmark_results)
            self.txt_proof.delete("1.0", tk.END)
            self.txt_proof.insert("1.0", md)

        if self.bench_engine.last_error:
            messagebox.showerror("Benchmark Error", self.bench_engine.last_error)

    def _copy_markdown(self):
        content = self.txt_proof.get("1.0", tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        messagebox.showinfo("Copied", "Markdown certificate copied to clipboard!")

    def _save_report(self):
        content = self.txt_proof.get("1.0", tk.END)
        path = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown", "*.md"), ("Text File", "*.txt")])
        if path:
            with open(path, "w") as f:
                f.write(content)
            messagebox.showinfo("Saved", f"Report saved to {path}")
