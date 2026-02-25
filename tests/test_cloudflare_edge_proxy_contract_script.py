from __future__ import annotations

import subprocess
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "check_cloudflare_edge_proxy_contract.sh"
)


def _run(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _write_workspace(tmp_path: Path) -> None:
    worker_path = tmp_path / "backend-cloudflare" / "src" / "worker.ts"
    api_client_path = tmp_path / "frontend-web" / "lib" / "api-client.ts"
    worker_path.parent.mkdir(parents=True, exist_ok=True)
    api_client_path.parent.mkdir(parents=True, exist_ok=True)

    worker_path.write_text(
        """
const ALLOWED_PATH_PREFIXES = ["/api/", "/ops/"];
const ALLOWED_EXACT_PATHS = new Set(["/healthz"]);
function createErrorResponse(traceId: string, policyReason: string | null) {
  return {
    error: {
      trace_id: traceId,
      policy_reason: policyReason,
    },
    headers: {
      "x-trace-id": traceId,
      "x-immcad-trace-id": traceId,
    },
  };
}
function withProxyResponseHeaders(headers: Headers, traceId: string) {
  headers.set("x-trace-id", traceId);
  headers.set("x-immcad-trace-id", traceId);
}
        """.strip(),
        encoding="utf-8",
    )
    api_client_path.write_text(
        """
function parseErrorEnvelope(payload: Record<string, unknown>) {
  if (typeof payload.error === "string") {
    const traceId = typeof payload.trace_id === "string" ? payload.trace_id : null;
    return { traceId };
  }
  return null;
}
function getResponseTraceId(headers: Headers): string | null {
  return headers.get("x-trace-id") ?? headers.get("x-immcad-trace-id");
}
        """.strip(),
        encoding="utf-8",
    )


def test_cloudflare_edge_proxy_contract_script_passes_on_expected_literals(
    tmp_path: Path,
) -> None:
    _write_workspace(tmp_path)
    result = _run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "Cloudflare edge proxy contract checks passed" in result.stdout


def test_cloudflare_edge_proxy_contract_script_fails_when_required_literal_missing(
    tmp_path: Path,
) -> None:
    _write_workspace(tmp_path)
    worker_path = tmp_path / "backend-cloudflare" / "src" / "worker.ts"
    worker_path.write_text(
        worker_path.read_text(encoding="utf-8").replace(
            'headers.set("x-trace-id", traceId);\n', ""
        ),
        encoding="utf-8",
    )
    result = _run(tmp_path)
    assert result.returncode == 1
    assert "Worker success proxy responses must emit x-trace-id header" in result.stderr
