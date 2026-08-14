# 💾 LinuxDisk — The CrystalDisk Unified Suite for Ubuntu & Linux

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Linux](https://img.shields.io/badge/Platform-Ubuntu%20%7C%20Debian%20%7C%20Fedora%20%7C%20Arch-black.svg)]()
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-green.svg)]()

**LinuxDisk** brings the complete functionality of **CrystalDiskInfo** (drive health, temperature & S.M.A.R.T. diagnostics) and **CrystalDiskMark** (direct unbuffered read/write speed benchmarking) to **Ubuntu Desktop and Linux**, featuring both a **Modern Dark Desktop GUI** and a **Rich Terminal TUI**.

Designed for storage power users, homelab enthusiasts, and hardware sellers looking to generate **verified proof of health and performance** for hard drives (such as 10TB Western Digital WD Red / Gold / Ultrastar / Elements) before selling online.

---

## ⚡ 1-Line Instant Install (Ubuntu / Debian / Fedora / Arch)

Open your terminal on Ubuntu/Linux and run:

```bash
curl -sSL https://raw.githubusercontent.com/alexuribarri/LinuxDisk/main/install.sh | bash
```

*(This automatically installs `smartmontools`, registers `/usr/local/bin/linuxdisk`, and adds the application shortcut to your Ubuntu Desktop App Grid!)*

---

## 🚀 Launch Instructions (Requires Sudo for Full S.M.A.R.T. Access)

Querying hardware S.M.A.R.T. controllers and raw disk blocks requires root/sudo privileges:

### 1. Launch Desktop GUI (Recommended)
```bash
sudo -E linuxdisk
```
*(The `-E` flag preserves your Ubuntu X11/Wayland display environment so the GUI opens smoothly).*

### 2. Launch Interactive Terminal TUI (SSH / Server Mode)
```bash
sudo linuxdisk --cli
```

---

## 🌟 Key Features

### 1. 🩺 CrystalDiskInfo Parity (Health & S.M.A.R.T.)
- **Health Shield & Score**: Real-time `GOOD (100%)`, `CAUTION`, or `BAD` grading.
- **Native USB S.M.A.R.T. Pass-Through**: Linux kernel SAT support allows reading **Power-On Hours**, **Temperature**, and bad sectors on **external USB Western Digital HDDs out-of-the-box**!
- **Critical HDD Metrics Verification**:
  - `ID 05` Reallocated Bad Sectors (0 Bad Sectors proof)
  - `ID C5` Current Pending Sectors
  - `ID C6` Offline Uncorrectable Sectors
- **Lifespan Counters**: Power-On Hours (converted to years, days, total hours), Power Cycles, and Real-time Temperature (°C / °F).
- **Interactive S.M.A.R.T. Table**: Searchable and filterable table with Hex/Decimal raw value toggles.

### 2. ⚡ CrystalDiskMark Parity (Speed Benchmark)
- **Direct Unbuffered I/O**: Disables page cache using POSIX `O_DIRECT` / `O_SYNC` and sector-aligned 4KB memory buffers (`mmap`) to test true disk hardware throughput.
- **Configurable Target Folder**: Target your mounted external drive (e.g. `/media/user/WD10TB`), custom directory, or `/tmp`.
- **Standard Test Profiles**:
  - `SEQ1M Q8T1` — Sequential 1MiB (Queues: 8, Threads: 1)
  - `SEQ1M Q1T1` — Sequential 1MiB (Queues: 1, Threads: 1)
  - `RND4K Q32T1` — Random 4KiB (Queues: 32, Threads: 1)
  - `RND4K Q1T1` — Random 4KiB (Queues: 1, Threads: 1)

### 3. 📦 Marketplace & Selling Proof Generator
- **1-Click Markdown Certificate**: Instant copy of formatted tables and bullet points ready to paste directly into eBay listings, Reddit r/Hardwareswap, or forum posts.
- **Export Diagnostic Report**: Save verified `.md` or `.txt` diagnostic certificates with timestamps.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
