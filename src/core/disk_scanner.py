import json
import subprocess
import os
import glob
from typing import List, Dict, Any
from .smart_engine import SmartEngine

class DiskScanner:
    """Discovers and inspects physical storage disks and mounted filesystems on Linux."""

    def __init__(self):
        self.smart_engine = SmartEngine()

    def scan_disks(self) -> List[Dict[str, Any]]:
        disks = []
        # Query lsblk with JSON output
        lsblk_disks = self._get_lsblk_disks()

        if lsblk_disks:
            for item in lsblk_disks:
                path = item.get("path") or f"/dev/{item.get('name')}"
                if not path:
                    continue

                smart_info = self.smart_engine.get_smart_data(path)
                
                # Capacity
                size_bytes = item.get("size") or 0
                if smart_info and smart_info.get("capacity_bytes"):
                    size_bytes = smart_info["capacity_bytes"]
                
                # Model
                model = item.get("model") or "Storage Disk"
                if smart_info and smart_info.get("model") and smart_info["model"] != "Unknown Drive":
                    model = smart_info["model"]

                # Serial
                serial = item.get("serial") or "Unknown"
                if smart_info and smart_info.get("serial") and smart_info["serial"] != "Unknown":
                    serial = smart_info["serial"]

                # Rotation / Type
                is_rotational = item.get("rota", True)
                rotation = "7200 RPM" if is_rotational else "Solid State (SSD)"
                if smart_info and smart_info.get("rotation_rate"):
                    rotation = smart_info["rotation_rate"]

                # Mountpoints
                mounts = self._collect_mountpoints(item)

                disk_entry = {
                    "path": path,
                    "name": item.get("name", os.path.basename(path)),
                    "model": model.strip(),
                    "serial": serial.strip(),
                    "size_bytes": size_bytes,
                    "size_formatted": self.format_bytes(size_bytes),
                    "rotation": rotation,
                    "transport": item.get("tran", "SATA/USB").upper(),
                    "mounts": mounts,
                    "smart": smart_info
                }
                disks.append(disk_entry)
        else:
            # Fallback via /sys/block
            disks = self._fallback_sysfs_scan()

        return disks

    def _get_lsblk_disks(self) -> List[Dict[str, Any]]:
        try:
            cmd = ["lsblk", "-J", "-b", "-o", "NAME,PATH,MODEL,SERIAL,SIZE,ROTA,TYPE,TRAN,MOUNTPOINTS"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout:
                data = json.loads(res.stdout)
                devices = data.get("blockdevices", [])
                # Only keep real physical disks (type == "disk")
                return [d for d in devices if d.get("type") == "disk" and not d.get("name", "").startswith("loop")]
        except Exception:
            pass
        return []

    def _collect_mountpoints(self, device_node: Dict[str, Any]) -> List[str]:
        mounts = []
        raw_mounts = device_node.get("mountpoints") or [device_node.get("mountpoint")]
        for m in raw_mounts:
            if m and isinstance(m, str) and m not in mounts:
                mounts.append(m)

        for child in device_node.get("children", []):
            child_mounts = child.get("mountpoints") or [child.get("mountpoint")]
            for cm in child_mounts:
                if cm and isinstance(cm, str) and cm not in mounts:
                    mounts.append(cm)
        return mounts

    def _fallback_sysfs_scan(self) -> List[Dict[str, Any]]:
        disks = []
        for sys_path in glob.glob("/sys/block/sd*") + glob.glob("/sys/block/nvme*n1"):
            name = os.path.basename(sys_path)
            dev_path = f"/dev/{name}"
            smart_info = self.smart_engine.get_smart_data(dev_path)

            size_bytes = 0
            size_file = os.path.join(sys_path, "size")
            if os.path.exists(size_file):
                with open(size_file, "r") as f:
                    sectors = int(f.read().strip() or 0)
                    size_bytes = sectors * 512

            disks.append({
                "path": dev_path,
                "name": name,
                "model": smart_info.get("model", "Disk") if smart_info else "Disk",
                "serial": smart_info.get("serial", "Unknown") if smart_info else "Unknown",
                "size_bytes": size_bytes,
                "size_formatted": self.format_bytes(size_bytes),
                "rotation": "7200 RPM" if "sd" in name else "Solid State (SSD)",
                "transport": "NVMe" if "nvme" in name else "SATA/USB",
                "mounts": ["/"],
                "smart": smart_info
            })
        return disks

    @staticmethod
    def format_bytes(bytes_val: int) -> str:
        if not bytes_val:
            return "0 Bytes"
        tb = bytes_val / (1000**4)
        gb = bytes_val / (1000**3)
        mb = bytes_val / (1000**2)
        if tb >= 1.0:
            return f"{tb:.1f} TB"
        elif gb >= 1.0:
            return f"{gb:.1f} GB"
        elif mb >= 1.0:
            return f"{mb:.1f} MB"
        return f"{bytes_val} B"
