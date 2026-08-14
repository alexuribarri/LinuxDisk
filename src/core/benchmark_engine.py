import os
import time
import mmap
import random
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

    def stop(self):
        self.should_stop = True

    def run_benchmark(
        self,
        target_dir: str,
        test_size_mb: int = 512,
        progress_cb: Optional[Callable[[str, float, Dict[str, Any]], None]] = None
    ) -> Dict[str, Dict[str, Any]]:
        self.should_stop = False
        results = {}
        temp_file = os.path.join(target_dir, ".linuxdisk_bench.tmp")

        total_tests = len(self.TEST_PROFILES) * 2  # Write + Read for each
        completed_steps = 0

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
                progress_cb(f"Testing {profile['name']} Write...", completed_steps / total_tests, results)

            write_res = self._execute_write(temp_file, profile, test_size_mb)
            if write_res:
                results[pid]["write_mbs"] = write_res["mbs"]
                results[pid]["write_iops"] = write_res["iops"]
                results[pid]["write_lat_us"] = write_res["lat_us"]

            completed_steps += 1
            if self.should_stop:
                break

            # 2. Read Test
            if progress_cb:
                progress_cb(f"Testing {profile['name']} Read...", completed_steps / total_tests, results)

            read_res = self._execute_read(temp_file, profile, test_size_mb)
            if read_res:
                results[pid]["read_mbs"] = read_res["mbs"]
                results[pid]["read_iops"] = read_res["iops"]
                results[pid]["read_lat_us"] = read_res["lat_us"]

            completed_steps += 1

        # Clean up temporary file
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception:
            pass

        if progress_cb:
            msg = "Benchmark Cancelled" if self.should_stop else "Benchmark Completed"
            progress_cb(msg, 1.0 if not self.should_stop else 0.0, results)

        return results

    def _execute_write(self, filepath: str, profile: Dict[str, Any], total_mb: int) -> Optional[Dict[str, float]]:
        block_size = profile["block_size"]
        total_bytes = min(total_mb, 512) * 1024 * 1024
        total_blocks = max(1, total_bytes // block_size)

        # Allocate 4096-byte aligned memory buffer using anonymous mmap
        buf = mmap.mmap(-1, block_size, mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS)
        # Fill buffer with random data
        buf.write(os.urandom(block_size))

        flags = os.O_RDWR | os.O_CREAT | os.O_TRUNC
        if hasattr(os, "O_DIRECT"):
            try:
                fd = os.open(filepath, flags | os.O_DIRECT, 0o666)
            except Exception:
                fd = os.open(filepath, flags | os.O_SYNC, 0o666)
        else:
            fd = os.open(filepath, flags | os.O_SYNC, 0o666)

        try:
            is_random = "RND" in profile["id"]
            start_time = time.perf_counter()
            written_bytes = 0

            if is_random:
                count = min(total_blocks, 4096)
                for _ in range(count):
                    if self.should_stop:
                        break
                    offset = random.randint(0, total_blocks - 1) * block_size
                    os.lseek(fd, offset, os.SEEK_SET)
                    written_bytes += os.write(fd, buf)
            else:
                for _ in range(total_blocks):
                    if self.should_stop:
                        break
                    written_bytes += os.write(fd, buf)

            os.fsync(fd)
            elapsed = time.perf_counter() - start_time
            if elapsed < 0.001:
                return {"mbs": 0.0, "iops": 0.0, "lat_us": 0.0}

            mbs = (written_bytes / (1024 * 1024)) / elapsed
            ops = written_bytes / block_size
            iops = ops / elapsed
            lat_us = (elapsed / max(ops, 1)) * 1_000_000.0

            return {"mbs": mbs, "iops": iops, "lat_us": lat_us}
        finally:
            os.close(fd)
            buf.close()

    def _execute_read(self, filepath: str, profile: Dict[str, Any], total_mb: int) -> Optional[Dict[str, float]]:
        if not os.path.exists(filepath):
            return None

        block_size = profile["block_size"]
        file_size = os.path.getsize(filepath)
        total_blocks = max(1, file_size // block_size)

        buf = mmap.mmap(-1, block_size, mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS)

        flags = os.O_RDONLY
        if hasattr(os, "O_DIRECT"):
            try:
                fd = os.open(filepath, flags | os.O_DIRECT)
            except Exception:
                fd = os.open(filepath, flags)
        else:
            fd = os.open(filepath, flags)

        try:
            is_random = "RND" in profile["id"]
            start_time = time.perf_counter()
            read_bytes = 0

            if is_random:
                count = min(total_blocks, 4096)
                for _ in range(count):
                    if self.should_stop:
                        break
                    offset = random.randint(0, total_blocks - 1) * block_size
                    os.lseek(fd, offset, os.SEEK_SET)
                    n = os.read(fd, block_size)
                    read_bytes += len(n)
            else:
                os.lseek(fd, 0, os.SEEK_SET)
                while read_bytes < file_size:
                    if self.should_stop:
                        break
                    n = os.read(fd, block_size)
                    if not n:
                        break
                    read_bytes += len(n)

            elapsed = time.perf_counter() - start_time
            if elapsed < 0.001:
                return {"mbs": 0.0, "iops": 0.0, "lat_us": 0.0}

            mbs = (read_bytes / (1024 * 1024)) / elapsed
            ops = read_bytes / block_size
            iops = ops / elapsed
            lat_us = (elapsed / max(ops, 1)) * 1_000_000.0

            return {"mbs": mbs, "iops": iops, "lat_us": lat_us}
        finally:
            os.close(fd)
            buf.close()
