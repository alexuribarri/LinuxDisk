import os
import time
import mmap
import random
import traceback
from typing import Dict, Any, Callable, Optional

class BenchmarkEngine:
    """High-performance unbuffered storage benchmark engine for Linux (CrystalDiskMark equivalent)."""

    TEST_PROFILES = [
        {"id": "SEQ1M_Q8T1", "name": "SEQ1M Q8T1", "block_size": 1024 * 1024, "queue": 8, "sub": "Sequential 1MiB (Q=8, T=1)"},
        {"id": "SEQ1M_Q1T1", "name": "SEQ1M Q1T1", "block_size": 1024 * 1024, "queue": 1, "sub": "Sequential 1MiB (Q=1, T=1)"},
        {"id": "RND4K_Q32T1", "name": "RND4K Q32T1", "block_size": 4 * 1024, "queue": 32, "sub": "Random 4KiB (Q=32, T=1)"},
        {"id": "RND4K_Q1T1", "name": "RND4K Q1T1", "block_size": 4 * 1024, "queue": 1, "sub": "Random 4KiB (Q=1, T=1)"},
    ]

    def __init__(self):
        self.should_stop = False
        self.last_error: Optional[str] = None

    def stop(self):
        self.should_stop = True

    def run_benchmark(
        self,
        target_dir: str,
        test_size_mb: int = 512,
        progress_cb: Optional[Callable[[str, float, Dict[str, Any]], None]] = None
    ) -> Dict[str, Dict[str, Any]]:
        self.should_stop = False
        self.last_error = None
        results = {}

        # Ensure target directory exists and is writable
        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir, exist_ok=True)
            except Exception as e:
                self.last_error = f"Cannot access target directory: {e}"
                if progress_cb:
                    progress_cb(f"Error: {self.last_error}", 0.0, {})
                return {}

        temp_file = os.path.join(target_dir, ".linuxdisk_bench.tmp")

        # Test write permission first
        try:
            with open(temp_file, "wb") as f:
                f.write(b"test")
            os.remove(temp_file)
        except Exception as e:
            self.last_error = f"Target directory is not writable ({e}). Select a mounted folder with write access."
            if progress_cb:
                progress_cb(f"Error: {self.last_error}", 0.0, {})
            return {}

        total_tests = len(self.TEST_PROFILES) * 2  # Write + Read for each
        completed_steps = 0

        # Cap test size for responsiveness (64MB to 512MB)
        actual_mb = max(64, min(test_size_mb, 512))

        for profile in self.TEST_PROFILES:
            if self.should_stop:
                break

            pid = profile["id"]
            results[pid] = {
                "profile": profile,
                "read_mbs": None,
                "write_mbs": None,
                "read_iops": None,
                "write_iops": None,
                "read_lat_us": None,
                "write_lat_us": None
            }

            # 1. Write Test
            if progress_cb:
                progress_cb(f"Writing {profile['name']} ({actual_mb}MB)...", completed_steps / total_tests, results)

            try:
                write_res = self._execute_write(temp_file, profile, actual_mb)
                if write_res:
                    results[pid]["write_mbs"] = write_res["mbs"]
                    results[pid]["write_iops"] = write_res["iops"]
                    results[pid]["write_lat_us"] = write_res["lat_us"]
            except Exception as e:
                self.last_error = f"Write error on {profile['name']}: {e}"

            completed_steps += 1
            if self.should_stop:
                break

            # 2. Read Test
            if progress_cb:
                progress_cb(f"Reading {profile['name']}...", completed_steps / total_tests, results)

            try:
                read_res = self._execute_read(temp_file, profile, actual_mb)
                if read_res:
                    results[pid]["read_mbs"] = read_res["mbs"]
                    results[pid]["read_iops"] = read_res["iops"]
                    results[pid]["read_lat_us"] = read_res["lat_us"]
            except Exception as e:
                self.last_error = f"Read error on {profile['name']}: {e}"

            completed_steps += 1

        # Clean up temporary test file
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception:
            pass

        if progress_cb:
            msg = "Benchmark Cancelled" if self.should_stop else ("Benchmark Finished" if not self.last_error else f"Finished ({self.last_error})")
            progress_cb(msg, 1.0 if not self.should_stop else 0.0, results)

        return results

    def _open_direct(self, filepath: str, flags: int) -> int:
        """Opens file attempting O_DIRECT, falling back to standard unbuffered sync if direct I/O is not supported by filesystem."""
        if hasattr(os, "O_DIRECT"):
            try:
                return os.open(filepath, flags | os.O_DIRECT, 0o666)
            except Exception:
                pass
        return os.open(filepath, flags | os.O_SYNC, 0o666)

    def _execute_write(self, filepath: str, profile: Dict[str, Any], total_mb: int) -> Optional[Dict[str, float]]:
        block_size = profile["block_size"]
        total_bytes = total_mb * 1024 * 1024
        total_blocks = max(1, total_bytes // block_size)

        # Prepare random buffer
        raw_data = os.urandom(block_size)

        flags = os.O_RDWR | os.O_CREAT | os.O_TRUNC
        fd = self._open_direct(filepath, flags)

        try:
            is_random = "RND" in profile["id"]
            start_time = time.perf_counter()
            written_bytes = 0

            if is_random:
                # Random write: seek to sector-aligned offsets
                count = min(total_blocks, 4096)
                for _ in range(count):
                    if self.should_stop:
                        break
                    offset = random.randint(0, max(0, total_blocks - 1)) * block_size
                    os.lseek(fd, offset, os.SEEK_SET)
                    w = os.write(fd, raw_data)
                    written_bytes += w
            else:
                # Sequential write
                for _ in range(total_blocks):
                    if self.should_stop:
                        break
                    w = os.write(fd, raw_data)
                    written_bytes += w

            os.fsync(fd)
            # Invalidate page cache if supported
            if hasattr(os, "posix_fadvise"):
                try:
                    os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
                except Exception:
                    pass

            elapsed = time.perf_counter() - start_time
            if elapsed < 0.001 or written_bytes == 0:
                return {"mbs": 0.0, "iops": 0.0, "lat_us": 0.0}

            mbs = (written_bytes / (1024 * 1024)) / elapsed
            ops = written_bytes / block_size
            iops = ops / elapsed
            lat_us = (elapsed / max(ops, 1)) * 1_000_000.0

            return {"mbs": mbs, "iops": iops, "lat_us": lat_us}
        finally:
            os.close(fd)

    def _execute_read(self, filepath: str, profile: Dict[str, Any], total_mb: int) -> Optional[Dict[str, float]]:
        if not os.path.exists(filepath):
            return None

        block_size = profile["block_size"]
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            return None

        total_blocks = max(1, file_size // block_size)

        fd = self._open_direct(filepath, os.O_RDONLY)

        # Invalidate page cache before reading to ensure physical disk I/O
        if hasattr(os, "posix_fadvise"):
            try:
                os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
            except Exception:
                pass

        try:
            is_random = "RND" in profile["id"]
            start_time = time.perf_counter()
            read_bytes = 0

            if is_random:
                count = min(total_blocks, 4096)
                for _ in range(count):
                    if self.should_stop:
                        break
                    offset = random.randint(0, max(0, total_blocks - 1)) * block_size
                    os.lseek(fd, offset, os.SEEK_SET)
                    chunk = os.read(fd, block_size)
                    read_bytes += len(chunk)
            else:
                os.lseek(fd, 0, os.SEEK_SET)
                while read_bytes < file_size:
                    if self.should_stop:
                        break
                    chunk = os.read(fd, block_size)
                    if not chunk:
                        break
                    read_bytes += len(chunk)

            elapsed = time.perf_counter() - start_time
            if elapsed < 0.001 or read_bytes == 0:
                return {"mbs": 0.0, "iops": 0.0, "lat_us": 0.0}

            mbs = (read_bytes / (1024 * 1024)) / elapsed
            ops = read_bytes / block_size
            iops = ops / elapsed
            lat_us = (elapsed / max(ops, 1)) * 1_000_000.0

            return {"mbs": mbs, "iops": iops, "lat_us": lat_us}
        finally:
            os.close(fd)
