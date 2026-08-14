import os
import sys
import time
from typing import List, Dict, Any
from ..core.disk_scanner import DiskScanner
from ..core.benchmark_engine import BenchmarkEngine
from ..core.exporter import ListingExporter

class TerminalUI:
    """Interactive, colorized terminal UI for LinuxDisk (works over SSH and headless servers)."""

    # ANSI Colors
    C_RESET = "\033[0m"
    C_BOLD = "\033[1m"
    C_DIM = "\033[2m"
    C_GREEN = "\033[92m"
    C_YELLOW = "\033[93m"
    C_RED = "\033[91m"
    C_BLUE = "\033[94m"
    C_CYAN = "\033[96m"
    C_WHITE = "\033[97m"
    C_BG_BLUE = "\033[44m"
    C_BG_GREEN = "\033[42m"

    def __init__(self):
        self.scanner = DiskScanner()
        self.bench_engine = BenchmarkEngine()

    def run(self):
        while True:
            self._clear_screen()
            self._print_header()
            disks = self.scanner.scan_disks()

            if not disks:
                print(f"\n{self.C_RED}No physical disks detected.{self.C_RESET}")
                print("Make sure you run with appropriate disk permissions (sudo).")
                input("\nPress Enter to exit...")
                return

            print(f"\n{self.C_BOLD}Available Disks:{self.C_RESET}")
            for idx, d in enumerate(disks):
                smart = d.get("smart") or {}
                grade = smart.get("health_grade", "GOOD")
                grade_color = self.C_GREEN if grade == "GOOD" else (self.C_RED if grade == "BAD" else self.C_YELLOW)
                print(f"  [{self.C_CYAN}{idx + 1}{self.C_RESET}] {self.C_BOLD}{d['model']}{self.C_RESET} ({d['size_formatted']}) - {d['path']} [{grade_color}{grade}{self.C_RESET}]")

            print(f"\n  [{self.C_RED}q{self.C_RESET}] Quit")
            choice = input(f"\n{self.C_BOLD}Select a disk (1-{len(disks)}): {self.C_RESET}").strip().lower()

            if choice == "q":
                break

            if choice.isdigit() and 1 <= int(choice) <= len(disks):
                self._show_disk_menu(disks[int(choice) - 1])

    def _show_disk_menu(self, disk: Dict[str, Any]):
        benchmark_results = {}
        while True:
            self._clear_screen()
            self._print_header()
            smart = disk.get("smart") or {}

            grade = smart.get("health_grade", "GOOD")
            score = smart.get("health_score", 100)
            grade_color = self.C_GREEN if grade == "GOOD" else (self.C_RED if grade == "BAD" else self.C_YELLOW)

            print(f"{self.C_BOLD}Selected Drive:{self.C_RESET} {self.C_CYAN}{disk.get('model')}{self.C_RESET} ({disk.get('path')})")
            print(f"Serial: {disk.get('serial', 'N/A')} | Size: {disk['size_formatted']} | Speed: {disk['rotation']}")
            print(f"Health: [{grade_color}{self.C_BOLD}{grade} {score}%{self.C_RESET}] | Temp: {smart.get('temperature', '--')} °C | Power-On: {smart.get('power_on_hours', '--')} hrs")
            
            realloc = smart.get('reallocated_sectors', 0)
            pending = smart.get('pending_sectors', 0)
            uncorr = smart.get('uncorrectable_sectors', 0)
            print(f"Bad Sectors (05): {self.C_GREEN if realloc == 0 else self.C_RED}{realloc}{self.C_RESET} | Pending (C5): {self.C_GREEN if pending == 0 else self.C_RED}{pending}{self.C_RESET} | Uncorrectable (C6): {self.C_GREEN if uncorr == 0 else self.C_RED}{uncorr}{self.C_RESET}")

            print(f"\n{self.C_BOLD}Actions:{self.C_RESET}")
            print(f"  [{self.C_CYAN}1{self.C_RESET}] View Full S.M.A.R.T. Attributes Table")
            print(f"  [{self.C_CYAN}2{self.C_RESET}] Run Speed Benchmark (CrystalDiskMark tests)")
            print(f"  [{self.C_CYAN}3{self.C_RESET}] Generate Marketplace Proof Certificate (Markdown)")
            print(f"  [{self.C_CYAN}4{self.C_RESET}] Back to Disks List")

            act = input(f"\n{self.C_BOLD}Choose action (1-4): {self.C_RESET}").strip()

            if act == "1":
                self._show_smart_table(smart)
            elif act == "2":
                mounts = disk.get("mounts", [])
                target = mounts[0] if mounts else "/tmp"
                print(f"\n{self.C_BOLD}Running benchmark on {target}...{self.C_RESET}")
                
                def on_prog(msg, prog, res):
                    pct = int(prog * 100)
                    sys.stdout.write(f"\r  [{pct}%] {msg:<40}")
                    sys.stdout.flush()

                benchmark_results = self.bench_engine.run_benchmark(target, 512, on_prog)
                print("\n\n" + ListingExporter.generate_markdown(disk, benchmark_results))
                input("\nPress Enter to continue...")
            elif act == "3":
                print("\n" + ListingExporter.generate_markdown(disk, benchmark_results))
                input("\nPress Enter to continue...")
            elif act == "4":
                break

    def _show_smart_table(self, smart: Dict[str, Any]):
        self._clear_screen()
        print(f"{self.C_BOLD}=== S.M.A.R.T. ATTRIBUTES TABLE ==={self.C_RESET}\n")
        attrs = smart.get("smart_attributes", [])
        if not attrs:
            print("No S.M.A.R.T. table returned for this drive.")
        else:
            print(f"{'ID':<6} {'Attribute Name':<32} {'Cur':<6} {'Wor':<6} {'Thr':<6} {'Raw Value':<16} {'Status'}")
            print("-" * 80)
            for a in attrs:
                status_color = self.C_GREEN if a['status'] == "GOOD" else self.C_RED
                print(f"{a['id_hex']:<6} {a['name']:<32} {a['current']:<6} {a['worst']:<6} {a['threshold']:<6} {a['raw_formatted']:<16} {status_color}{a['status']}{self.C_RESET}")

        input("\nPress Enter to return...")

    def _clear_screen(self):
        os.system("clear" if os.name == "posix" else "cls")

    def _print_header(self):
        print(f"{self.C_BG_BLUE}{self.C_WHITE}{self.C_BOLD}   💾 LinuxDisk — CrystalDisk Unified Suite for Ubuntu / Linux   {self.C_RESET}\n")
