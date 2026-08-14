import json
import subprocess
import shutil
from typing import Dict, Any, List, Optional

class SmartEngine:
    """Core S.M.A.R.T. querying and parsing engine for Linux storage devices."""

    def __init__(self):
        self.smartctl_path = shutil.which("smartctl") or "/usr/sbin/smartctl"

    def get_smart_data(self, device_path: str) -> Optional[Dict[str, Any]]:
        """Queries smartctl in JSON mode with automatic SAT fallback for external USB drives."""
        if not shutil.which(self.smartctl_path):
            return None

        # Try default, then SAT (SCSI-ATA translation for USB), then auto
        attempts = [
            [self.smartctl_path, "-j", "-a", device_path],
            [self.smartctl_path, "-j", "-a", "-d", "sat", device_path],
            [self.smartctl_path, "-j", "-a", "-d", "auto", device_path],
            [self.smartctl_path, "-j", "-a", "-d", "scsi", device_path],
        ]

        for cmd in attempts:
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
                if res.stdout:
                    data = json.loads(res.stdout)
                    parsed = self._parse_json(data, device_path)
                    if parsed and (parsed.get("smart_attributes") or parsed.get("model")):
                        return parsed
            except Exception:
                continue

        return None

    def _parse_json(self, json_data: Dict[str, Any], device_path: str) -> Optional[Dict[str, Any]]:
        model = json_data.get("model_name") or json_data.get("device", {}).get("name", "Unknown Drive")
        serial = json_data.get("serial_number", "Unknown")
        firmware = json_data.get("firmware_version", "Unknown")

        # Capacity
        capacity_bytes = 0
        user_cap = json_data.get("user_capacity", {})
        if isinstance(user_cap, dict) and "bytes" in user_cap:
            capacity_bytes = user_cap["bytes"]

        # Rotation Rate
        rot = json_data.get("rotation_rate")
        if rot == 0:
            rotation_rate = "Solid State (SSD)"
        elif rot:
            rotation_rate = f"{rot} RPM"
        else:
            rotation_rate = "Solid State (SSD)" if "nvme" in device_path.lower() else "7200 RPM"

        # Interface
        dev_type = json_data.get("device", {}).get("type", "").lower()
        if "nvme" in dev_type or "nvme" in device_path:
            interface = "NVMe"
            rotation_rate = "Solid State (SSD)"
        elif "sat" in dev_type or "ata" in dev_type:
            interface = "SATA"
        else:
            interface = "SATA / USB"

        # Temperature
        temperature = None
        temp_dict = json_data.get("temperature", {})
        if isinstance(temp_dict, dict) and "current" in temp_dict:
            temperature = temp_dict["current"]

        # Power On Hours & Cycles
        power_on_hours = None
        power_cycles = None
        poh_dict = json_data.get("power_on_time", {})
        if isinstance(poh_dict, dict) and "hours" in poh_dict:
            power_on_hours = poh_dict["hours"]

        if "power_cycle_count" in json_data:
            power_cycles = json_data["power_cycle_count"]

        # Parse ATA Attributes Table
        attributes = []
        reallocated_count = 0
        pending_count = 0
        uncorrectable_count = 0

        ata_table = json_data.get("ata_smart_attributes", {}).get("table", [])
        for row in ata_table:
            attr_id = row.get("id")
            name = row.get("name", f"Attribute {attr_id}")
            current = row.get("value", 100)
            worst = row.get("worst", 100)
            thresh = row.get("thresh", 0)

            raw = row.get("raw", {})
            raw_val = raw.get("value", 0) if isinstance(raw, dict) else 0
            raw_str = raw.get("string", str(raw_val)) if isinstance(raw, dict) else str(raw_val)

            status = "GOOD"
            interpretation = ""
            is_critical = False

            # Inspect critical HDD health metrics
            if attr_id == 5:  # Reallocated Sectors Count
                is_critical = True
                reallocated_count = raw_val
                if raw_val > 0:
                    status = "BAD" if raw_val > 20 else "CAUTION"
                    interpretation = f"{raw_val} bad sectors reallocated."
                else:
                    interpretation = "0 bad sectors (Pristine condition)"
            elif attr_id in (197, 0xC5):  # Current Pending Sector Count
                is_critical = True
                pending_count = raw_val
                if raw_val > 0:
                    status = "CAUTION"
                    interpretation = f"{raw_val} unstable sectors pending relocation."
                else:
                    interpretation = "0 pending sectors (Stable)"
            elif attr_id in (198, 0xC6):  # Offline Uncorrectable
                is_critical = True
                uncorrectable_count = raw_val
                if raw_val > 0:
                    status = "BAD"
                    interpretation = f"{raw_val} uncorrectable sectors."
                else:
                    interpretation = "0 uncorrectable errors"
            elif attr_id == 9:  # Power On Hours
                if power_on_hours is None:
                    power_on_hours = raw_val
            elif attr_id == 12:  # Power Cycles
                if power_cycles is None:
                    power_cycles = raw_val
            elif attr_id in (194, 0xC2):  # Temperature
                if temperature is None:
                    temperature = raw_val & 0xFF

            attributes.append({
                "id": attr_id,
                "id_hex": f"{attr_id:02X}",
                "name": name,
                "current": current,
                "worst": worst,
                "threshold": thresh,
                "raw_value": raw_val,
                "raw_formatted": raw_str,
                "is_critical": is_critical,
                "status": status,
                "interpretation": interpretation
            })

        # Parse NVMe Health Information Log (if SSD)
        nvme_log = json_data.get("nvme_smart_health_information_log", {})
        if nvme_log:
            interface = "NVMe"
            rotation_rate = "Solid State (SSD)"
            if "temperature" in nvme_log:
                temperature = nvme_log["temperature"]
            if "percentage_used" in nvme_log:
                wear = nvme_log["percentage_used"]
                attributes.append({
                    "id": 1,
                    "id_hex": "01",
                    "name": "Percentage Used (Wear Level)",
                    "current": 100 - min(wear, 100),
                    "worst": 100 - min(wear, 100),
                    "threshold": 0,
                    "raw_value": wear,
                    "raw_formatted": f"{wear}%",
                    "is_critical": True,
                    "status": "CAUTION" if wear > 90 else "GOOD",
                    "interpretation": f"{100 - min(wear, 100)}% life remaining"
                })
            if "available_spare" in nvme_log:
                spare = nvme_log["available_spare"]
                attributes.append({
                    "id": 2,
                    "id_hex": "02",
                    "name": "Available Spare Blocks",
                    "current": spare,
                    "worst": spare,
                    "threshold": nvme_log.get("available_spare_threshold", 10),
                    "raw_value": spare,
                    "raw_formatted": f"{spare}%",
                    "is_critical": True,
                    "status": "BAD" if spare < 10 else "GOOD",
                    "interpretation": "Flash reserve capacity"
                })
            if "data_units_read" in nvme_log:
                tb_read = (nvme_log["data_units_read"] * 1000 * 512) / (1024**4)
                attributes.append({
                    "id": 3,
                    "id_hex": "03",
                    "name": "Total Host Reads",
                    "current": 100,
                    "worst": 100,
                    "threshold": 0,
                    "raw_value": nvme_log["data_units_read"],
                    "raw_formatted": f"{tb_read:.2f} TB",
                    "is_critical": False,
                    "status": "GOOD",
                    "interpretation": "Lifetime data read"
                })
            if "data_units_written" in nvme_log:
                tb_written = (nvme_log["data_units_written"] * 1000 * 512) / (1024**4)
                attributes.append({
                    "id": 4,
                    "id_hex": "04",
                    "name": "Total Host Writes (TBW)",
                    "current": 100,
                    "worst": 100,
                    "threshold": 0,
                    "raw_value": nvme_log["data_units_written"],
                    "raw_formatted": f"{tb_written:.2f} TB",
                    "is_critical": False,
                    "status": "GOOD",
                    "interpretation": "Lifetime data written"
                })
            if "power_on_hours" in nvme_log:
                power_on_hours = nvme_log["power_on_hours"]
            if "power_cycles" in nvme_log:
                power_cycles = nvme_log["power_cycles"]

        # Health Grade Calculation
        health_grade = "GOOD"
        health_score = 100
        reasons = []

        if reallocated_count > 0:
            if reallocated_count > 20:
                health_grade = "BAD"
                health_score = 40
                reasons.append(f"Critical: {reallocated_count} Reallocated Sectors detected.")
            else:
                health_grade = "CAUTION"
                health_score = 75
                reasons.append(f"Warning: {reallocated_count} Reallocated Sectors detected.")

        if pending_count > 0:
            if health_grade != "BAD":
                health_grade = "CAUTION"
            health_score = min(health_score, 70)
            reasons.append(f"{pending_count} Unstable Pending Sectors.")

        if uncorrectable_count > 0:
            health_grade = "BAD"
            health_score = min(health_score, 35)
            reasons.append(f"{uncorrectable_count} Offline Uncorrectable Sectors.")

        if not reasons:
            reasons.append("All S.M.A.R.T. health parameters verified optimal. 0 bad sectors.")

        return {
            "device": device_path,
            "model": model,
            "serial": serial,
            "firmware": firmware,
            "capacity_bytes": capacity_bytes,
            "interface": interface,
            "rotation_rate": rotation_rate,
            "temperature": temperature,
            "power_on_hours": power_on_hours,
            "power_cycles": power_cycles,
            "reallocated_sectors": reallocated_count,
            "pending_sectors": pending_count,
            "uncorrectable_sectors": uncorrectable_count,
            "health_grade": health_grade,
            "health_score": health_score,
            "health_reasons": reasons,
            "smart_attributes": attributes
        }
