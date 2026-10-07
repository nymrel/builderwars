"""Script-free judge report for one live Nebius/NVIDIA receipt."""
from __future__ import annotations

from html import escape


def _yn(value):
    return "Yes" if value else "No"


def render_live_receipt_report(receipt):
    evidence = receipt["runtimeEvidence"]
    evaluation = receipt["evaluation"]
    checks = evaluation.get("checks", [])
    rows = "".join(
        "<tr>"
        f"<td>{escape(check['case'])}</td>"
        f"<td class=\"{'pass' if check['passed'] else 'fail'}\">"
        f"{'PASS' if check['passed'] else 'FAIL'}</td>"
        "</tr>"
        for check in checks
    )
    score = evaluation.get("score")
    score_text = (
        f"{score['passed']} / {score['total']}" if isinstance(score, dict) else "invalid response"
    )
    status = escape(str(receipt["status"]).upper())
    status_class = "pass" if receipt["status"] == "passed" else "fail"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; connect-src 'none'; media-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'">
  <title>BuilderWars · Nebius NVIDIA live proof</title>
  <style>
    :root {{ color-scheme: dark; font-family: ui-sans-serif, system-ui, sans-serif; background:#0d1110; color:#edf4ef; }}
    body {{ margin:0; }} main {{ width:min(920px,calc(100% - 32px)); margin:auto; padding:44px 0 64px; }}
    h1 {{ font-size:clamp(2rem,7vw,4.5rem); line-height:.95; letter-spacing:-.05em; }}
    h2 {{ margin-top:34px; }} .eyebrow,.label {{ color:#91a69a; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:12px; }}
    .card {{ border:1px solid #2f3c35; border-radius:14px; padding:18px; background:#151b18; overflow-wrap:anywhere; }}
    .label {{ display:block; font-size:.8rem; margin-bottom:7px; }} .value {{ font-weight:750; }}
    .pass {{ color:#7ce09d; font-weight:800; }} .fail {{ color:#ff9a9a; font-weight:800; }}
    table {{ width:100%; border-collapse:collapse; background:#151b18; border:1px solid #2f3c35; }}
    th,td {{ padding:11px 13px; text-align:left; border-bottom:1px solid #2f3c35; }}
    th {{ color:#91a69a; font-size:.8rem; }} code {{ overflow-wrap:anywhere; }}
    .notice {{ margin-top:28px; border-left:3px solid #e6b566; background:#211d15; color:#f4dfbb; padding:15px 17px; }}
  </style>
</head>
<body><main>
  <p class="eyebrow">BuilderWars · Open Agent Proof Arena</p>
  <h1>Nebius × NVIDIA live run</h1>
  <section class="grid" aria-label="Run summary">
    <div class="card"><span class="label">Outcome</span><span class="value {status_class}">{status}</span></div>
    <div class="card"><span class="label">Score</span><span class="value">{escape(score_text)}</span></div>
    <div class="card"><span class="label">Model</span><span class="value">{escape(receipt['model'])}</span></div>
    <div class="card"><span class="label">Observed</span><span class="value">{escape(receipt['observedAt'])}</span></div>
  </section>

  <h2>Runtime evidence</h2>
  <section class="grid">
    <div class="card"><span class="label">Nebius HTTPS call observed by runner</span><span class="value">{_yn(evidence['providerCallObserved'])}</span></div>
    <div class="card"><span class="label">NVIDIA model execution observed by runner</span><span class="value">{_yn(evidence['modelExecutionObservedByRunner'])}</span></div>
    <div class="card"><span class="label">Credential value retained</span><span class="value">{_yn(evidence['credentialValueRetained'])}</span></div>
    <div class="card"><span class="label">Raw model response retained</span><span class="value">{_yn(evidence['rawResponseRetained'])}</span></div>
  </section>

  <h2>Deterministic checks</h2>
  <table><thead><tr><th scope="col">Case</th><th scope="col">Result</th></tr></thead><tbody>{rows}</tbody></table>

  <h2>Bindings</h2>
  <div class="card">
    <p><span class="label">Endpoint</span><code>{escape(receipt['endpoint'])}</code></p>
    <p><span class="label">Task digest</span><code>{escape(receipt['taskDigest'])}</code></p>
    <p><span class="label">Prompt digest</span><code>{escape(receipt['promptDigest'])}</code></p>
    <p><span class="label">Response-text digest</span><code>{escape(receipt['responseTextDigest'])}</code></p>
    <p><span class="label">Live receipt digest</span><code>{escape(receipt['receiptDigest'])}</code></p>
  </div>

  <p class="notice">This receipt is a runner-observed record, not a provider-signed attestation. It proves only what this runner observed for this exact call and deterministic evaluation. It does not expose or retain the API key or raw model response.</p>
</main></body></html>
"""
