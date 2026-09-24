"""Browser-rendered, labeled user-flow evaluation for Sightline.

Serves tracked BuilderWars Mobile Arena source only on loopback, captures
representative UI-state regressions in Chromium, evaluates them with OpenCV 5,
emits classification metrics and a digest-bound receipt, and deletes every PNG
when the process exits.
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
from typing import Any, Callable, Iterator
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
EVALUATION_ROOT = Path(__file__).resolve().parent
MOBILE_ARENA = ROOT / "mobile-arena"
SIGHTLINE_PATH = EVALUATION_ROOT / "sightline.py"
VIEWPORT = {"width": 1040, "height": 900}
SOURCE_HEAD_ENV = "SOURCE_HEAD"


@dataclass(frozen=True)
class UserFlowCase:
    name: str
    workflow: str
    regression: str
    expected_material: bool
    observed_material: bool
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
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
        )
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
    spec = importlib.util.spec_from_file_location(
        "sightline_browser_core", SIGHTLINE_PATH
    )
    if not spec or not spec.loader:
        raise RuntimeError("could not load Sightline core")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _stabilize(page: Any) -> None:
    page.evaluate(
        """() => {
            const style = document.createElement('style');
            style.textContent = '*{animation:none!important;transition:none!important;caret-color:transparent!important}';
            document.head.appendChild(style);
            window.scrollTo(0, 0);
        }"""
    )


def _reset(page: Any, url: str) -> None:
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


def _capture(page: Any, path: Path) -> None:
    page.screenshot(path=str(path), full_page=False, animations="disabled")


def _require_visible(page: Any, selector: str) -> None:
    locator = page.locator(selector)
    locator.wait_for(state="visible")
    box = locator.bounding_box()
    if not box or box["width"] * box["height"] < 10_000:
        raise RuntimeError(f"workflow target {selector!r} is missing or too small")


def _evaluate_pair(
    *,
    sightline: Any,
    perception: Any,
    name: str,
    workflow: str,
    regression: str,
    expected_material: bool,
    baseline: Path,
    candidate: Path,
) -> UserFlowCase:
    findings = perception.analyze_files(
        baseline,
        candidate,
        threshold=24,
        min_component_pixels=64,
    )
    trace = sightline.SightlineAgent().plan(findings)
    observed_material = bool(findings)
    expected_action = (
        "request_human_approval"
        if expected_material
        else "accept_no_material_change"
    )
    passed = (
        observed_material is expected_material
        and trace.action == expected_action
        and trace.human_approval_required is expected_material
        and not trace.execution_authorized
        and not trace.aws_invoked
    )
    return UserFlowCase(
        name=name,
        workflow=workflow,
        regression=regression,
        expected_material=expected_material,
        observed_material=observed_material,
        observed_kinds=tuple(finding.kind for finding in findings),
        action=trace.action,
        human_approval_required=trace.human_approval_required,
        baseline_sha256=_digest(baseline),
        candidate_sha256=_digest(candidate),
        findings_sha256=trace.findings_sha256,
        passed=passed,
    )


def _confusion(cases: list[UserFlowCase]) -> dict[str, int | float]:
    true_positive = sum(
        case.expected_material and case.observed_material for case in cases
    )
    true_negative = sum(
        not case.expected_material and not case.observed_material for case in cases
    )
    false_positive = sum(
        not case.expected_material and case.observed_material for case in cases
    )
    false_negative = sum(
        case.expected_material and not case.observed_material for case in cases
    )
    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative
    specificity_denominator = true_negative + false_positive
    total = len(cases)
    return {
        "true_positive": true_positive,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": true_positive / precision_denominator
        if precision_denominator
        else 0.0,
        "recall": true_positive / recall_denominator if recall_denominator else 0.0,
        "specificity": true_negative / specificity_denominator
        if specificity_denominator
        else 0.0,
        "accuracy": (true_positive + true_negative) / total if total else 0.0,
    }


def evaluate() -> dict[str, Any]:
    source_head = os.environ.get(SOURCE_HEAD_ENV, "").strip()
    if len(source_head) != 40 or any(
        char not in "0123456789abcdef" for char in source_head
    ):
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

            captures: list[
                tuple[str, str, str, bool, Path, Path]
            ] = []

            def record(
                name: str,
                workflow: str,
                regression: str,
                expected_material: bool,
                mutate: Callable[[Any], None] | None,
            ) -> None:
                _reset(page, url)
                baseline = root / f"{name}-baseline.png"
                candidate = root / f"{name}-candidate.png"
                _capture(page, baseline)
                if mutate is not None:
                    mutate(page)
                _capture(page, candidate)
                captures.append(
                    (
                        name,
                        workflow,
                        regression,
                        expected_material,
                        baseline,
                        candidate,
                    )
                )

            record(
                "arena_stable",
                "inspect the Arena landing view",
                "none",
                False,
                None,
            )

            def remove_featured(current_page: Any) -> None:
                _require_visible(current_page, "#featured-match")
                current_page.evaluate(
                    """() => {
                        const target = document.querySelector('#featured-match');
                        target.style.visibility = 'hidden';
                    }"""
                )

            record(
                "featured_receipt_missing",
                "inspect the featured reviewed receipt",
                "featured receipt region disappears",
                True,
                remove_featured,
            )

            def open_session_sheet(current_page: Any) -> None:
                _require_visible(current_page, "#profile-button")
                current_page.locator("#profile-button").click()
                _require_visible(current_page, "#session-sheet")

            record(
                "session_sheet_unexpected",
                "review the Arena while the local-session sheet should remain closed",
                "local-session sheet appears unexpectedly",
                True,
                open_session_sheet,
            )

            def route_to_wrong_view(current_page: Any) -> None:
                _require_visible(current_page, "[data-nav='watch']")
                current_page.locator("[data-nav='watch']").click()
                _require_visible(current_page, "#view-watch")

            record(
                "primary_view_misroute",
                "open the Arena primary destination",
                "navigation resolves to Watch instead of Arena",
                True,
                route_to_wrong_view,
            )

            cases = [
                _evaluate_pair(
                    sightline=sightline,
                    perception=perception,
                    name=name,
                    workflow=workflow,
                    regression=regression,
                    expected_material=expected_material,
                    baseline=baseline,
                    candidate=candidate,
                )
                for (
                    name,
                    workflow,
                    regression,
                    expected_material,
                    baseline,
                    candidate,
                ) in captures
            ]
            context.close()
            browser.close()

    if external_requests:
        raise RuntimeError("browser corpus attempted a cross-origin request")
    if console_errors:
        raise RuntimeError(
            f"browser corpus emitted console warnings/errors: {console_errors!r}"
        )

    confusion = _confusion(cases)
    passed = sum(case.passed for case in cases)
    all_passed = (
        passed == len(cases)
        and confusion["false_positive"] == 0
        and confusion["false_negative"] == 0
    )
    return {
        "schema": "sightline.browser-user-flow-evaluation.v2",
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
        "scope": "loopback_browser_rendered_labeled_user_flows",
        "task_success": {
            "passed": passed,
            "total": len(cases),
            "rate": passed / len(cases),
        },
        "confusion_matrix": confusion,
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
