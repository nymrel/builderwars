"""Record a genuine, bounded Sightline user-journey demonstration.

Only tracked Nymrel source is served on loopback. Each displayed measurement is
computed from a fresh browser screenshot with the existing OpenCV 5 adapter.
Approval is an explicitly labeled automated demo-operator event, never a claim
that an actual human authorized a production action. No AWS API is called.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import struct
import subprocess
import time
from typing import Any

import cv2
import numpy as np
from playwright.async_api import async_playwright

from aws_lambda_handler import lambda_handler
from demo_approval import DEMO_ACTION, DemoApprovalGate
from evaluate_browser_corpus import loopback_server
from sightline import OpenCV5Perception, SightlineAgent


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TARGET = "#featured-match"
VIEWPORT = {"width": 1040, "height": 900}
SCREEN = {"width": 1600, "height": 900}


def digest(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def png_url(payload: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(payload).decode("ascii")


def thumbnail_hash(value: str) -> str:
    return f"SHA-256 · {value[:20]}…"


def git_source() -> dict[str, Any]:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, check=True, text=True, capture_output=True
    )
    head = result.stdout.strip()
    paths = sorted(
        [path for path in (REPO / "mobile-arena").rglob("*") if path.is_file()]
        + [HERE / name for name in (
            "sightline.py", "aws_lambda_handler.py", "demo_approval.py",
            "journey_demo.html", "record_journey_demo.py",
        )]
    )
    files = [{"path": str(path.relative_to(REPO)), "sha256": digest(path.read_bytes())} for path in paths]
    return {
        "repository": "https://github.com/nymrel/builderwars",
        "base_commit": head,
        "worktree_files_sha256": digest(json_bytes(files)),
        "files": files,
        "ownership_basis": "tracked_nymrel_source_under_MIT_and_new_Nymrel_demonstration_code",
    }


class Journey:
    def __init__(self, output: Path, app: Any, source: dict[str, Any]) -> None:
        self.output = output
        self.app = app
        self.source = source
        self.perception = OpenCV5Perception()
        self.agent = SightlineAgent()
        self.stage = 0
        self.gate: DemoApprovalGate | None = None
        self.findings = []
        self.trace = None
        self.events: list[dict[str, Any]] = []
        self.failure_controls: list[dict[str, Any]] = []
        self.caption_events: list[dict[str, Any]] = []
        self.started = time.monotonic()
        self.baseline = b""
        self.candidate = b""
        self.restored = b""
        self.original_visibility = ""
        self.verification: dict[str, Any] | None = None

    async def capture(self, name: str) -> bytes:
        payload = await self.app.screenshot(full_page=False, animations="disabled")
        (self.output / name).write_bytes(payload)
        return payload

    def event(self, name: str, **values: Any) -> None:
        self.events.append({"event": name, **values})

    def caption(self, content: str) -> str:
        self.caption_events.append({"start_seconds": round(time.monotonic() - self.started, 3), "text": content})
        return content

    async def prepare(self, url: str) -> dict[str, Any]:
        await self.app.goto(url, wait_until="domcontentloaded")
        await self.app.wait_for_function("() => document.body.dataset.sourceMode === 'verified_corpus'")
        await self.app.evaluate("""() => {
            const style=document.createElement('style');
            style.textContent='*{animation:none!important;transition:none!important;caret-color:transparent!important}';
            document.head.appendChild(style);
        }""")
        await self.app.locator(TARGET).scroll_into_view_if_needed()
        self.original_visibility = await self.app.locator(TARGET).evaluate("node => node.style.visibility")
        self.baseline = await self.capture("baseline.png")
        await self.app.locator(TARGET).evaluate("""node => {
            node.style.visibility='hidden';
            node.dataset.sightlineDemoInjected='true';
        }""")
        self.candidate = await self.capture("candidate.png")
        if digest(self.baseline) == digest(self.candidate):
            raise RuntimeError("the intended controlled fault was not visible")
        self.event("controlled_fault_injected", target=TARGET, fault="visibility_hidden", source="tracked_builderwars_dom")
        return {
            "step": 0,
            "images": {"baseline": png_url(self.baseline), "observed": png_url(self.candidate)},
            "text": {
                "baseline-hash": thumbnail_hash(digest(self.baseline)),
                "observed-hash": thumbnail_hash(digest(self.candidate)),
                "source": f"BuilderWars · {self.source['base_commit'][:12]} · Firefox 146",
                "caption": self.caption("The page still loads, but its featured receipt has disappeared. This controlled fault uses the real tracked BuilderWars interface."),
            },
        }

    async def perform(self, name: str) -> dict[str, Any]:
        allowed = {
            0: "inspect", 1: "attempt", 2: "approve", 3: "apply", 4: "verify",
            5: "failures", 6: "limits", 7: "cloud", 8: "finish",
        }
        if allowed.get(self.stage) != name:
            raise PermissionError("action is out of order for this measured demo session")
        if name == "inspect":
            self.findings = self.perception.analyze_files(
                self.output / "baseline.png", self.output / "candidate.png",
                threshold=24, min_component_pixels=64,
            )
            self.trace = self.agent.plan(self.findings)
            if self.trace.action != "request_human_approval":
                raise RuntimeError("controlled missing-receipt case did not request approval")
            self.gate = DemoApprovalGate(
                findings_sha256=self.trace.findings_sha256,
                candidate_sha256=digest(self.candidate),
            )
            overlay = cv2.imdecode(np.frombuffer(self.candidate, dtype=np.uint8), cv2.IMREAD_COLOR)
            for finding in self.findings:
                x, y, width, height = finding.bbox_xywh
                cv2.rectangle(overlay, (x, y), (x + width, y + height), (85, 185, 255), 2)
            okay, encoded = cv2.imencode(".png", overlay)
            if not okay:
                raise RuntimeError("could not encode evidence annotation")
            (self.output / "opencv-evidence.png").write_bytes(encoded.tobytes())
            self.event("opencv_diagnostic_decision", findings=[asdict(f) for f in self.findings], decision=asdict(self.trace))
            self.stage = 1
            return {
                "step": 1, "statusClass": "stop",
                "images": {"observed": png_url(encoded.tobytes())},
                "text": {
                    "step-label": "02 / Detect and decide",
                    "headline": "OpenCV measures the defect. The policy stops.",
                    "status": self.trace.action,
                    "decision": "Review the missing receipt before changing anything.",
                    "finding-count": str(len(self.findings)),
                    "changed-pixels": f"{sum(f.changed_pixels for f in self.findings):,}",
                    "observed-hash": f"Input {thumbnail_hash(digest(self.candidate))}",
                    "digest": f"findings_sha256: {self.trace.findings_sha256}",
                    "caption": self.caption("OpenCV 5 computes absolute differences, thresholds the mask, and extracts connected components. Deterministic policy requests approval; it cannot modify the app."),
                },
                "html": {
                    "observed-label": "Observed + evidence overlay<span>Measured components</span>",
                    "details": "<p>Amber boxes are measured connected components, not inferred objects.</p><p><strong>Bounded diagnostic proposal:</strong> inspect the featured receipt, then restore only the injected visibility change in this temporary browser.</p><p>Known fault injection supplies the cause; pixel evidence alone does not prove it.</p>",
                    "controls": '<button id="attempt" class="secondary">Try restore without approval</button>',
                },
            }
        if name == "attempt":
            assert self.gate is not None
            before = await self.capture("before-denied-attempt.png")
            try:
                self.gate.consume(action=DEMO_ACTION, current_candidate_sha256=digest(before))
            except PermissionError as exc:
                error = str(exc)
            else:
                raise RuntimeError("unapproved action was not blocked")
            after = await self.capture("after-denied-attempt.png")
            unchanged = digest(before) == digest(after) == digest(self.candidate)
            if not unchanged:
                raise RuntimeError("browser changed during rejected action")
            self.event("unapproved_action_rejected", error=error, before_sha256=digest(before), after_sha256=digest(after), image_unchanged=True)
            self.stage = 2
            return {
                "step": 2, "statusClass": "stop",
                "text": {
                    "step-label": "03 / Enforce the boundary", "headline": "No approval means no action.",
                    "status": "action_rejected", "decision": "The blocked attempt leaves the view unchanged.",
                    "digest": f"before == after: {digest(after)}",
                    "caption": self.caption("The restore is attempted without approval and rejected. Matching before/after screenshot hashes verify that the blocked attempt changed nothing."),
                },
                "html": {
                    "details": "<p>The approval gate binds one action to this candidate image and findings digest.</p><p>A different action, changed candidate, or reused approval is rejected.</p><p>The next event is scripted for this demonstration. It is not evidence of a human approval or production authorization.</p>",
                    "controls": '<label><input id="approval-check" type="checkbox">Record a labeled demo-operator approval for one local fixture restore only.</label><button id="approve" disabled>Record demo operator approval</button>',
                },
            }
        if name == "approve":
            assert self.gate is not None
            approval = self.gate.record_demo_operator_event()
            self.event("demo_operator_approval", **approval)
            self.stage = 3
            return {
                "step": 3, "statusClass": "",
                "text": {
                    "step-label": "04 / Record explicit scope", "headline": "One reviewed action. One temporary fixture.",
                    "status": "demo_approval_recorded", "decision": "Approval is separate from the diagnostic engine.",
                    "digest": "actor: automated_demo_operator\nhuman_approval_observed: false\nproduction_authority: false",
                    "caption": self.caption("This recorded click is an automated demo-operator event. It grants one local fixture restore, with no repository, cloud, billing, or production authority."),
                },
                "html": {
                    "details": "<p><strong>Approved action:</strong> restore the injected visibility property of this one receipt.</p><p><strong>Scope:</strong> this temporary browser DOM only.</p><p>The grant is bound to the measured candidate and is consumed once. Sightline's planner still has no write authority.</p>",
                    "controls": '<button id="apply">Apply approved local fixture restore</button>',
                },
            }
        if name == "apply":
            assert self.gate is not None
            current = await self.capture("before-approved-restore.png")
            approved = self.gate.consume(action=DEMO_ACTION, current_candidate_sha256=digest(current))
            marker = await self.app.locator(TARGET).get_attribute("data-sightline-demo-injected")
            if marker != "true":
                raise RuntimeError("the controlled fixture marker is missing")
            await self.app.locator(TARGET).evaluate("""(node, value) => {
                node.style.visibility = value;
                delete node.dataset.sightlineDemoInjected;
            }""", self.original_visibility)
            self.restored = await self.capture("restored.png")
            self.event("approved_demo_fixture_restored", approval=asdict(approved), restored_sha256=digest(self.restored), verified=False)
            self.stage = 4
            return {
                "step": 4, "statusClass": "",
                "images": {"observed": png_url(self.restored)},
                "text": {
                    "step-label": "05 / Observe the proposed repair", "headline": "The receipt is back. Verification is still pending.",
                    "status": "restore_applied_not_verified", "decision": "A completed action is not yet a verified outcome.",
                    "observed-hash": thumbnail_hash(digest(self.restored)),
                    "digest": "action_scope: temporary DOM only\nverification: pending\nagent execution_authorized: false",
                    "caption": self.caption("The isolated fixture controller restores the one injected property. Sightline does not call that success yet: it must measure a fresh screenshot against the original baseline."),
                },
                "html": {"observed-label": "Fresh observed view<span>After local restore</span>", "details": "<p>The repair is a controlled undo of a known injected fault, not general autonomous remediation.</p><p>A new screenshot has been captured. Re-run the same OpenCV threshold and decision policy to check it.</p>", "controls": '<button id="verify">Verify the fresh outcome</button>'},
            }
        if name == "verify":
            fresh = await self.capture("verified.png")
            findings = self.perception.analyze_files(self.output / "baseline.png", self.output / "verified.png", threshold=24, min_component_pixels=64)
            trace = self.agent.plan(findings)
            identical = digest(fresh) == digest(self.baseline)
            if findings or trace.action != "accept_no_material_change" or not identical:
                raise RuntimeError("restored outcome did not match the initial measured view")
            self.verification = {"findings": [asdict(f) for f in findings], "decision": asdict(trace), "fresh_screenshot_sha256": digest(fresh), "baseline_sha256": digest(self.baseline), "pixel_identical_to_baseline": identical, "passed": True}
            self.event("fresh_outcome_verified", **self.verification)
            self.stage = 5
            return {
                "step": 5, "statusClass": "good",
                "text": {
                    "step-label": "06 / Verify the outcome", "headline": "Zero remaining findings. Baseline restored.",
                    "status": trace.action, "decision": "Verified for this exact fixture and viewport.",
                    "finding-count": "0", "changed-pixels": "0",
                    "digest": f"baseline == verified: {digest(fresh)}",
                    "caption": self.caption("A fresh OpenCV pass returns zero retained components. The new screenshot is also byte-identical to the baseline. This proves the outcome for this controlled fixture, not production accuracy."),
                },
                "html": {"details": "<p><strong>Observe → diagnose → explicit approval boundary → bounded local action → re-measure.</strong></p><p>The outcome is tied to the actual PNGs, source snapshot, runtime versions, and decision digests.</p><p>The original defective input and all failed/denied steps remain in the evidence.</p>", "controls": '<button id="failures" class="secondary">Check failure handling</button>'},
            }
        if name == "failures":
            assert self.baseline
            # Use the exact bounded handler, including pre-decode IHDR checks.
            baseline64 = base64.b64encode(self.baseline).decode("ascii")
            cases = [
                ("Malformed PNG", "must be a PNG image with an IHDR chunk", {"baseline_png_base64": "bm90LXBvbmc=", "candidate_png_base64": baseline64}),
                ("Dimension mismatch", "dimensions must match", {"baseline_png_base64": baseline64, "candidate_png_base64": self._different_dimension_png()}),
                ("Compressed expansion", "dimensions exceed 4096px", {"baseline_png_base64": baseline64, "candidate_png_base64": self._oversize_header_png()}),
            ]
            for label, expected, event in cases:
                try:
                    lambda_handler(event, None)
                except ValueError as exc:
                    result = {"error_type": "ValueError", "message": str(exc)}
                    if expected not in str(exc):
                        raise RuntimeError(f"{label} stopped for an unexpected reason") from exc
                else:
                    raise RuntimeError(f"{label} was not rejected by the handler")
                self.failure_controls.append({"name": label, "response": result, "passed": True})
            self.event("bounded_input_failures_verified", controls=self.failure_controls)
            self.stage = 6
            return {
                "step": 6, "statusClass": "good",
                "text": {
                    "step-label": "07 / Preserve failure evidence", "headline": "Unsafe inputs stop before a proposal.",
                    "status": "3_fail_closed_controls_passed", "decision": "Invalid images are errors, never successful decisions.",
                    "digest": "handler: three ValueError rejections\nvalid outcome: separately measured\nAWS invoked: false",
                    "caption": self.caption("The existing bounded handler rejects malformed PNGs, unequal dimensions, and a small payload declaring oversized dimensions. These failures remain visible in the receipt."),
                },
                "html": {"details": "<table><tr><td>Malformed PNG</td><td>Rejected</td></tr><tr><td>Dimension mismatch</td><td>Rejected</td></tr><tr><td>Compressed expansion</td><td>Rejected</td></tr></table><p style='margin-top:16px'>The prior PNG expansion vulnerability was fixed in the merged implementation. We retain it as an adversarial regression.</p>", "controls": '<button id="limits" class="secondary">Show the measurement limits</button>'},
            }
        if name == "limits":
            self.stage = 7
            return {
                "step": 7, "statusClass": "",
                "text": {
                    "step-label": "08 / State what the evidence covers", "headline": "A reproducible slice, with its limits intact.",
                    "status": "controlled_evidence_only", "decision": "No production-accuracy or autonomous-repair claim.",
                    "digest": "Historical defects retained:\nfragmented materiality · below-fold framing\nfixture polarity · compressed PNG expansion",
                    "caption": self.caption("The evaluation is small and controlled. Prior false negatives, capture-framing mistakes, reversed fixture polarity, and the PNG expansion issue are preserved in the record, not erased."),
                },
                "html": {"details": "<ul><li>One repaired fixture and one fixed viewport in this walkthrough.</li><li>Current Firefox corpus: 12 cases, six workflow types, two viewports; 10 TP and 2 TN.</li><li>Historic Chromium results stay separate from this local rerun.</li><li>Pixels do not establish semantic intent or the root cause of an unknown defect.</li></ul>", "controls": '<button id="cloud" class="secondary">Show the AWS truth boundary</button>'},
            }
        if name == "cloud":
            self.stage = 8
            return {
                "step": 8, "statusClass": "stop",
                "text": {
                    "step-label": "09 / Separate compatibility from execution", "headline": "This recording is local. AWS execution remains unverified.",
                    "status": "aws_runtime_evidence_missing", "decision": "The source ZIP is not a cloud-runtime receipt.",
                    "digest": "recording_environment: local\nmeaningful_aws_execution_verified: false\ncompetition_submission_verified: false",
                    "caption": self.caption("This walkthrough makes no AWS execution claim. Actual AWS runtime logs and reproducible invocation evidence must be added separately before this can satisfy the competition's cloud requirement."),
                },
                "html": {"details": "<p>OpenCV comparison and policy are Lambda-compatible, but this run is local.</p><p>An authorized AWS run must preserve the exact source, dependencies, input hashes, returned findings, and runtime identity.</p><p>No AWS call, billing change, cloud spend, or Devpost submission occurs in this demonstration.</p>", "controls": '<button id="finish">Finish the measured walkthrough</button>'},
            }
        self.stage = 9
        return {
            "step": 8, "statusClass": "good",
            "text": {
                "headline": "See the defect. Bound the decision. Verify the outcome.",
                "status": "local_journey_complete", "decision": "Sightline keeps the evidence and the approval boundary visible.",
                "caption": self.caption("Sightline by Nymrel: a measured visual troubleshooting journey on BuilderWars, with explicit control, retained failure evidence, and an honestly verified local outcome."),
            },
            "html": {"controls": "<div style='font-size:15px;color:#9eb5cf'>OpenCV 5.0.0 · deterministic policy · MIT source<br>Controlled local demonstration</div>"},
        }

    def _different_dimension_png(self) -> str:
        okay, encoded = cv2.imencode(".png", np.zeros((16, 16, 3), dtype=np.uint8))
        if not okay:
            raise RuntimeError("cannot encode mismatch control")
        return base64.b64encode(encoded.tobytes()).decode("ascii")

    def _oversize_header_png(self) -> str:
        # Pre-decode header rejection: under 1 MiB, declares 4097 x 1 pixels.
        payload = bytearray(self.baseline[:33])
        payload[16:24] = struct.pack(">II", 4097, 1)
        return base64.b64encode(payload).decode("ascii")


async def record(output: Path, hold_scale: float, browser_engine: str) -> dict[str, Any]:
    if cv2.__version__ != "5.0.0" or np.__version__ != "2.3.5":
        raise RuntimeError("use the existing exact, hash-locked OpenCV/NumPy environment")
    output.mkdir(parents=True, exist_ok=True)
    source = git_source()
    external_requests: list[str] = []
    warnings: list[str] = []
    with loopback_server() as url:
        async with async_playwright() as runtime:
            browser = await getattr(runtime, browser_engine).launch(headless=True)
            browser_version = browser.version
            app_context = await browser.new_context(viewport=VIEWPORT, device_scale_factor=1, color_scheme="dark", reduced_motion="reduce", locale="en-US")
            await app_context.add_init_script("localStorage.setItem('builderwars.mobile-arena.starter-guide.v1','complete')")
            async def only_loopback(route: Any) -> None:
                from urllib.parse import urlparse
                parsed = urlparse(route.request.url)
                if parsed.scheme in {"http", "https"} and parsed.hostname not in {"127.0.0.1", "localhost"}:
                    external_requests.append(route.request.url)
                    await route.abort()
                else:
                    await route.continue_()
            await app_context.route("**/*", only_loopback)
            app = await app_context.new_page()
            app.on("console", lambda message: warnings.append(message.text) if message.type in {"error", "warning"} else None)
            journey = Journey(output, app, source)
            initial = await journey.prepare(url)
            initial["text"]["source"] = f"BuilderWars · {source['base_commit'][:12]} · {browser_engine} {browser_version}"
            demo_context = await browser.new_context(viewport=SCREEN, device_scale_factor=1, color_scheme="dark", reduced_motion="reduce", record_video_dir=str(output / "raw-video"), record_video_size=SCREEN)
            demo = await demo_context.new_page()
            await demo.expose_function("performDemoAction", journey.perform)
            await demo.set_content((HERE / "journey_demo.html").read_text(encoding="utf-8"))
            journey.started = time.monotonic()
            await demo.evaluate("value => window.fill(value)", initial)
            await demo.screenshot(path=str(output / "01-observe.png"))
            await asyncio.sleep(12 * hold_scale)
            sequence = [
                ("inspect", 1, 19), ("attempt", 2, 17), ("approve", 3, 15),
                ("apply", 4, 14), ("verify", 5, 20), ("failures", 6, 18),
                ("limits", 7, 22), ("cloud", 8, 17), ("finish", 8, 9),
            ]
            for action, stage, hold in sequence:
                if action == "approve":
                    await demo.locator("#approval-check").check()
                    await asyncio.sleep(2 * hold_scale)
                await demo.locator(f"#{action}").click()
                if action == "finish":
                    await demo.wait_for_function("() => document.getElementById('status').textContent === 'local_journey_complete'")
                else:
                    await demo.wait_for_function("stage => document.body.dataset.step === String(stage)", arg=stage)
                if await demo.get_attribute("body", "data-error"):
                    raise RuntimeError("the displayed demo stopped on an error")
                await demo.screenshot(path=str(output / f"{stage + 1:02d}-{action}.png"))
                await asyncio.sleep(hold * hold_scale)
            elapsed = time.monotonic() - journey.started
            video = demo.video
            assert video is not None
            await demo_context.close()
            await video.save_as(str(output / "sightline-local-walkthrough.webm"))
            await app_context.close()
            await browser.close()
    if external_requests or warnings:
        raise RuntimeError("unexpected external request or browser warning; inspect private runtime logs")
    if journey.verification is None or not journey.verification["passed"]:
        raise RuntimeError("the journey did not produce a verified outcome")
    artifact_files = sorted(path for path in output.iterdir() if path.is_file())
    receipt = {
        "schema": "sightline.local-journey.v1",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "runtime": {"opencv": cv2.__version__, "numpy": np.__version__, "playwright": "1.58.0", "browser": browser_engine, "browser_version": browser_version, "source_viewport": VIEWPORT, "recording_viewport": SCREEN},
        "scope": "controlled_fault_in_tracked_local_builderwars",
        "events": journey.events,
        "verification": journey.verification,
        "failure_controls": journey.failure_controls,
        "captions": journey.caption_events,
        "approximately_recorded_seconds": round(elapsed, 3),
        "artifacts": [{"path": path.name, "bytes": path.stat().st_size, "sha256": digest(path.read_bytes())} for path in artifact_files],
        "production_accuracy_claimed": False,
        "autonomous_remediation_claimed": False,
        "human_approval_observed": False,
        "approval_actor": "automated_demo_operator",
        "external_requests": 0,
        "browser_warnings_or_errors": 0,
        "aws_invoked": False,
        "meaningful_aws_execution_verified": False,
        "submitted_to_devpost": False,
        "all_local_checks_passed": True,
        "limitations": [
            "single injected fault on one tracked source surface at one fixed viewport",
            "cause known from injection; pixels alone do not establish unknown root cause",
            "approval click is automated and explicitly labeled, not actual human approval",
            "remedy restores only the injected temporary DOM property",
            "pixel equality for a controlled fixture is not general production accuracy",
            "local runtime is not AWS execution or Devpost submission evidence",
        ],
        "prior_failure_evidence_retained": [
            "fragmented-materiality false negative; conservative aggregate/component guards added",
            "below-fold mobile framing error; targeted workflow scrolled into view",
            "reversed synthetic visual polarity; fixture corrected without threshold weakening",
            "compressed PNG expansion vulnerability; pre-decode IHDR bounds added",
        ],
    }
    (output / "journey-receipt.json").write_bytes(json_bytes(receipt))
    return {"receipt": "journey-receipt.json", "video": "sightline-local-walkthrough.webm", "all_local_checks_passed": True, "aws_invoked": False, "human_approval_observed": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--hold-scale", type=float, default=1.0, help="0.02 is useful for a quick verification recording")
    parser.add_argument("--browser", choices=("firefox", "chromium"), default="firefox")
    args = parser.parse_args()
    if args.hold_scale <= 0:
        parser.error("hold scale must be positive")
    print(json.dumps(asyncio.run(record(args.output_dir.resolve(), args.hold_scale, args.browser)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
