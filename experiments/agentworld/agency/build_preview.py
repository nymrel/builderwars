"""Bundle the local agency playground into one offline HTML file."""
import argparse
import base64
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build(output: Path) -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    hashes = []
    for filename in ["../engine.js", "policy.js", "app.js"]:
        script = (ROOT / filename).read_text(encoding="utf-8")
        if "</script" in script.lower():
            raise ValueError("Script contains an unsafe HTML closing tag")
        tag = f'<script src="{filename}"></script>'
        if html.count(tag) != 1:
            raise ValueError(f"Expected one script reference: {filename}")
        digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
        hashes.append(f"'sha256-{digest}'")
        html = html.replace(tag, "<script>" + script + "</script>")
    if html.count("script-src 'self'") != 1:
        raise ValueError("Expected one script CSP directive")
    html = html.replace("script-src 'self'", "script-src " + " ".join(hashes))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    print(f"Built {output} ({len(html.encode())} bytes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    build(parser.parse_args().output)
