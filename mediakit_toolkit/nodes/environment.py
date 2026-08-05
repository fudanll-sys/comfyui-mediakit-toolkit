"""Read-only MediaKit environment diagnostic node."""

from __future__ import annotations

import json
import platform
import shutil

from comfy_api.latest import io

from ..cli import cli_version, find_cli, run_cli
from ..redaction import redact_text


class MediaKitEnvironmentCheck(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MediaKitEnvironmentCheck",
            display_name="MediaKit Environment Check",
            category="MediaKit/Diagnostics",
            description="检查 MediaKit CLI、凭证和本地运行环境，不会输出 API Key。",
            inputs=[
                io.Boolean.Input("run_doctor", default=True),
            ],
            outputs=[
                io.String.Output(display_name="status"),
                io.String.Output(display_name="details_json"),
            ],
        )

    @classmethod
    def execute(cls, run_doctor: bool = True) -> io.NodeOutput:
        details: dict[str, object] = {
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
            "node": shutil.which("node"),
            "npm": shutil.which("npm"),
        }
        try:
            details["mediakit_cli"] = find_cli()
            details["mediakit_cli_version"] = cli_version()
            if run_doctor:
                doctor = run_cli(["doctor"], timeout=120, expect_json=False)
                details["doctor_ok"] = doctor.returncode == 0
                details["doctor_output"] = redact_text(
                    (doctor.stdout or doctor.stderr)[-5000:]
                )
            status = "ready" if details.get("doctor_ok", True) else "warning"
        except Exception as exc:  # Diagnostic nodes return details instead of failing.
            details["error"] = redact_text(str(exc))
            status = "not_ready"
        return io.NodeOutput(status, json.dumps(details, ensure_ascii=False, indent=2))

