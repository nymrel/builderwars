"""Human-readable, offline report for one structured-patch receipt."""

from __future__ import annotations

from html import escape


_BOUNDARY_LABELS = {
    "generatedCodeExecuted": "Generated code executed",
    "providerCallObserved": "Provider call observed",
    "credentialObserved": "Credential observed",
    "rawResponseRetained": "Raw response retained",
}


def _yes_no(value):
    return "Yes" if value else "No"


def render_receipt_report(receipt):
    """Return a deterministic, script-free HTML inspection report.

    The report is a projection of the existing receipt. It does not add claims,
    retain the model response, or fetch any external resource.
    """

    checks = "".join(
        "<tr>"
        f"<td>{escape(check['case'])}</td>"
        f"<td class=\"{'pass' if check['passed'] else 'fail'}\">"
        f"{'PASS' if check['passed'] else 'FAIL'}</td>"
        "</tr>"
        for check in receipt["checks"]
    )
    boundaries = "".join(
        "<li>"
        f"<span>{escape(_BOUNDARY_LABELS[key])}</span>"
        f"<strong>{_yes_no(receipt['boundary'][key])}</strong>"
        "</li>"
        for key in _BOUNDARY_LABELS
    )
    status = escape(receipt["status"].upper())
    status_class = "pass" if receipt["status"] == "passed" else "fail"
    passed = receipt["score"]["passed"]
    total = receipt["score"]["total"]

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; connect-src 'none'; media-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'">
  <title>BuilderWars evaluation receipt</title>
  <style>
    :root {{ color-scheme: dark; font-family: ui-sans-serif, system-ui, sans-serif; background: #0d1110; color: #edf4ef; }}
    body {{ margin: 0; }}
    main {{ width: min(880px, calc(100% - 32px)); margin: 0 auto; padding: 48px 0 64px; }}
    h1 {{ font-size: clamp(2rem, 7vw, 4.5rem); line-height: .95; margin: 12px 0 24px; letter-spacing: -.05em; }}
    h2 {{ margin-top: 36px; }}
    .eyebrow {{ color: #91a69a; letter-spacing: .12em; text-transform: uppercase; font-size: .78rem; }}
    .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
    .card {{ border: 1px solid #2f3c35; border-radius: 14px; padding: 18px; background: #151b18; }}
    .label {{ display: block; color: #91a69a; font-size: .8rem; margin-bottom: 8px; }}
    .value {{ font-size: 1.25rem; font-weight: 700; overflow-wrap: anywhere; }}
    table {{ width: 100%; border-collapse: collapse; background: #151b18; border: 1px solid #2f3c35; }}
    th, td {{ padding: 12px 14px; text-align: left; border-bottom: 1px solid #2f3c35; }}
    th {{ color: #91a69a; font-size: .8rem; }}
    .pass {{ color: #7ce09d; font-weight: 800; }}
    .fail {{ color: #ff9a9a; font-weight: 800; }}
    ul {{ list-style: none; padding: 0; margin: 0; }}
    li {{ display: flex; justify-content: space-between; gap: 24px; padding: 11px 0; border-bottom: 1px solid #2f3c35; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: .85rem; overflow-wrap: anywhere; }}
    .notice {{ margin-top: 32px; padding: 16px 18px; border-left: 3px solid #e6b566; background: #211d15; color: #f4dfbb; }}
  </style>
</head>
<body>
<main>
  <p class="eyebrow">BuilderWars · Open Agent Proof Arena</p>
  <h1>Evaluation receipt</h1>
  <section class="summary" aria-label="Evaluation summary">
    <div class="card"><span class="label">Outcome</span><span class="value {status_class}">{status}</span></div>
    <div class="card"><span class="label">Score</span><span class="value">{passed} / {total}</span></div>
    <div class="card"><span class="label">Provider label</span><span class="value">{escape(receipt['provider'])}</span></div>
    <div class="card"><span class="label">Model label</span><span class="value">{escape(receipt['model'])}</span></div>
  </section>

  <h2>Checks</h2>
  <table>
    <thead><tr><th scope="col">Case</th><th scope="col">Result</th></tr></thead>
    <tbody>{checks}</tbody>
  </table>

  <h2>Evidence boundary</h2>
  <div class="card"><ul>{boundaries}</ul></div>

  <h2>Bindings</h2>
  <div class="card">
    <p><span class="label">Task</span><code>{escape(receipt['taskVersion'])}</code></p>
    <p><span class="label">Task digest</span><code>{escape(receipt['taskDigest'])}</code></p>
    <p><span class="label">Response digest</span><code>{escape(receipt['responseDigest'])}</code></p>
    <p><span class="label">Result policy digest</span><code>{escape(receipt['resultPolicyDigest'])}</code></p>
    <p><span class="label">Receipt digest</span><code>{escape(receipt['receiptDigest'])}</code></p>
  </div>

  <p class="notice">This report proves only the deterministic evaluator result encoded in this receipt. It does not prove a provider call, credential use, model quality, deployment, or competition submission.</p>
</main>
</body>
</html>
"""
