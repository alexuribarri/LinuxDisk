import sys
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description="LinuxDisk — CrystalDisk Unified Suite for Ubuntu / Linux")
    parser.add_argument("--cli", "--tui", action="store_true", help="Launch in interactive Terminal UI mode")
    parser.add_argument("--version", action="version", version="LinuxDisk 1.0.0")
    args = parser.parse_args()

    # Determine if GUI should run (DISPLAY or WAYLAND_DISPLAY available and tkinter present)
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    run_tui = args.cli or not has_display

    if not run_tui:
        try:
            import tkinter as tk
            from .gui.main_window import LinuxDiskGUI
            root = tk.Tk()
            app = LinuxDiskGUI(root)
            root.mainloop()
            return
        except Exception as e:
            print(f"Note: GUI unavailable ({e}), falling back to Terminal UI.\n")

    # Launch Terminal UI
    from .tui.terminal_ui import TerminalUI
    tui = TerminalUI()
    tui.run()

if __name__ == "__main__":
    main()
