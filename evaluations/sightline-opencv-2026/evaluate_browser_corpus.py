"""Browser-rendered, provenance-bounded Sightline evaluation.

Serves tracked BuilderWars Mobile Arena source only on loopback, captures
controlled visual regressions in Chromium, evaluates them with OpenCV 5, emits a
digest-bound receipt, and deletes every PNG when the process exits.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from functools import partial
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from typing import Any, Iterator
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
EVALUATION_ROOT = Path(__file__).resolve().parent
MOBILE_ARENA = ROOT / "mobile-arena"
SIGHTLINE_PATH = EVALUATION_ROOT / "sightline.py"
VIEWPORT = {"width": 1040, "height": 900}
SOURCE_HEAD_ENV = "SOURCE_HEAD"
EXPECTED_CASES = {
    "no_change": (),
    "missing_region": ("missing_region",),
    "unexpected_region": ("unexpected_region",),
    "layout_shift": ("layout_shift", "layout_shift"),
}


@dataclass(frozen=True)
class BrowserCase:
    name: str
    expected_kinds: tuple[str, ...]
    observed_kinds: tuple[str, ...]
    action: str
    human_approval_required: bool
    baseline_sha256: str
    candidate_sha256: str
    findings_sha256: str
    passed: bool


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'")
        super().end_headers()


@contextmanager
def loopback_server() -> Iterator[str]:
    if not MOBILE_ARENA.is_dir():
        raise RuntimeError("tracked mobile-arena source is missing")
    handler = partial(QuietHandler, directory=str(MOBILE_ARENA))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}/index.html"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if thread.is_alive():
            raise RuntimeError("loopback server did not stop")


def _load_sightline() -> Any:
    spec = importlib.util.spec_from_file_location("sightline_browser_core", SIGHTLINE_PATH)
    if not spec or not spec.loader:
        raise RuntimeError("could not load Sightline core")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _marker_script(left: int) -> str:
    return f"""() => {{
        document.querySelector('#sightline-controlled-marker')?.remove();
        const marker = document.createElement('div');
        marker.id = 'sightline-controlled-marker';
        marker.setAttribute('aria-hidden', 'true');
        marker.style.cssText = [
            'position:fixed',
            'left:{left}px',
            'top:660px',
            'width:260px',
            'height:110px',
            'background:#ffffff',
            'border-radius:12px',
            'box-shadow:none',
            'z-index:2147483647'
        ].join(';');
        document.body.appendChild(marker);
    }}"""


def _stabilize(page: Any) -> None:
    page.evaluate(
        """() => {
            const style = document.createElement('style');
            style.textContent = '*{animation:none!important;transition:none!important;caret-color:transparent!important}';
            document.head.appendChild(style);
            window.scrollTo(0, 0);
        }"""
    )


def _capture(page: Any, path: Path, marker_left: int | None) -> None:
    page.evaluate("() => document.querySelector('#sightline-controlled-marker')?.remove()")
    if marker_left is not None:
        page.evaluate(_marker_script(marker_left))
    page.screenshot(path=str(path), full_page=False, animations="disabled")


def _evaluate_pair(
    *,
    sightline: Any,
    perception: Any,
    name: str,
    baseline: Path,
    candidate: Path,
) -> BrowserCase:
    findings = perception.analyze_files(
        baseline,
        candidate,
        threshold=24,
        min_component_pixels=64,
    )
    trace = sightline.SightlineAgent().plan(findings)
    observed = tuple(finding.kind for finding in findings)
    expected = EXPECTED_CASES[name]
    material = bool(expected)
    passed = (
        observed == expected
        and trace.action
        == ("request_human_approval" if material else "accept_no_material_change")
        and trace.human_approval_required is material
        and not trace.execution_authorized
        and not trace.aws_invoked
    )
    return BrowserCase(
        name=name,
        expected_kinds=expected,
        observed_kinds=observed,
        action=trace.action,
        human_approval_required=trace.human_approval_required,
        baseline_sha256=_digest(baseline),
        candidate_sha256=_digest(candidate),
        findings_sha256=trace.findings_sha256,
        passed=passed,
    )


def evaluate() -> dict[str, Any]:
    source_head = os.environ.get(SOURCE_HEAD_ENV, "").strip()
    if len(source_head) != 40 or any(char not in "0123456789abcdef" for char in source_head):
        raise RuntimeError("SOURCE_HEAD must be an exact lowercase 40-character Git SHA")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("playwright 1.58.0 is required for browser evaluation") from exc

    sightline = _load_sightline()
    perception = sightline.OpenCV5Perception()
    if perception.cv2.__version__ != "5.0.0":
        raise RuntimeError(
            f"exact OpenCV 5.0.0 required; observed {perception.cv2.__version__}"
        )

    external_requests: list[str] = []
    console_errors: list[str] = []
    with tempfile.TemporaryDirectory() as directory, loopback_server() as url:
        root = Path(directory)
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True)
            context = browser.new_context(
                viewport=VIEWPORT,
                device_scale_factor=1,
                color_scheme="dark",
                reduced_motion="reduce",
                locale="en-US",
            )
            page = context.new_page()

            def observe_request(request: Any) -> None:
                parsed = urlparse(request.url)
                if parsed.scheme in {"http", "https"} and parsed.hostname not in {
                    "127.0.0.1",
                    "localhost",
                }:
                    external_requests.append(request.url)

            page.on("request", observe_request)
            page.on(
                "console",
                lambda message: console_errors.append(message.text)
                if message.type in {"error", "warning"}
                else None,
            )
            page.add_init_script(
                """() => localStorage.setItem(
                    'builderwars.mobile-arena.starter-guide.v1',
                    'complete'
                )"""
            )
            response = page.goto(url, wait_until="domcontentloaded")
            if response is None or not response.ok:
                raise RuntimeError("loopback BuilderWars shell did not return HTTP success")
            page.wait_for_function(
                "() => document.body.dataset.sourceMode && document.body.dataset.sourceMode !== 'loading'"
            )
            source_mode = page.evaluate("() => document.body.dataset.sourceMode")
            if source_mode != "verified_corpus":
                raise RuntimeError(f"expected verified_corpus source, observed {source_mode!r}")
            _stabilize(page)

            images: dict[str, tuple[Path, Path]] = {}
            for name, baseline_marker, candidate_marker in (
                ("no_change", None, None),
                ("missing_region", 80, None),
                ("unexpected_region", None, 80),
                ("layout_shift", 80, 650),
            ):
                baseline = root / f"{name}-baseline.png"
                candidate = root / f"{name}-candidate.png"
                _capture(page, baseline, baseline_marker)
                _capture(page, candidate, candidate_marker)
                images[name] = (baseline, candidate)

            cases = [
                _evaluate_pair(
                    sightline=sightline,
                    perception=perception,
                    name=name,
                    baseline=images[name][0],
                    candidate=images[name][1],
                )
                for name in EXPECTED_CASES
            ]
            context.close()
            browser.close()

    if external_requests:
        raise RuntimeError("browser corpus attempted a cross-origin request")
    if console_errors:
        raise RuntimeError(f"browser corpus emitted console warnings/errors: {console_errors!r}")

    passed = sum(case.passed for case in cases)
    all_passed = passed == len(cases)
    return {
        "schema": "sightline.browser-evaluation.v1",
        "source": {
            "repository": "nymrel/builderwars",
            "commit": source_head,
            "path": "mobile-arena",
            "ownership_basis": "tracked_nymrel_source",
        },
        "runtime": {
            "opencv": perception.cv2.__version__,
            "browser": "chromium",
            "playwright": "1.58.0",
            "viewport": VIEWPORT,
        },
        "scope": "loopback_browser_rendered_controlled_stage1",
        "task_success": {
            "passed": passed,
            "total": len(cases),
            "rate": passed / len(cases),
        },
        "cases": [asdict(case) for case in cases],
        "external_requests": 0,
        "console_warnings_or_errors": 0,
        "pngs_persisted": False,
        "production_accuracy_claimed": False,
        "aws_invoked": False,
        "execution_authorized": False,
        "all_passed": all_passed,
    }


def main() -> int:
    result = evaluate()
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
