"""Build a self-contained GENZA presentation.

Reads index.html (source, relative image paths) and writes
GENZA-presentation.html with every local image inlined as a data URI,
so the single file can be emailed / opened anywhere.

Usage:  python build.py
"""
import base64
import io
import pathlib
import re

from PIL import Image

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "index.html"
OUT = ROOT / "GENZA-presentation.html"

MOCKUP_MAX_W = 1200
JPEG_QUALITY = 82


def _has_alpha(im: Image.Image) -> bool:
    """True when the image actually uses its transparency channel."""
    if im.mode not in ("RGBA", "LA", "PA"):
        return False
    return im.getchannel("A").getextrema()[0] < 255


def data_uri(path: pathlib.Path) -> str:
    """PNGs that carry alpha stay PNG (the cut-out logos); everything else
    gets resized and re-encoded as progressive JPEG."""
    im = Image.open(path)

    if _has_alpha(im):
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

    if im.width > MOCKUP_MAX_W:
        im = im.resize(
            (MOCKUP_MAX_W, round(im.height * MOCKUP_MAX_W / im.width)),
            Image.LANCZOS,
        )
    if im.mode != "RGB":
        im = im.convert("RGB")
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def main() -> None:
    html = SRC.read_text(encoding="utf-8")
    found = set()

    def repl(match: re.Match) -> str:
        raw = match.group(1)
        if raw.startswith(("http://", "https://", "data:", "#")):
            return match.group(0)
        name = raw.replace("%20", " ")
        path = ROOT / name
        if not path.exists():
            raise SystemExit(f"missing asset: {name}")
        found.add(name)
        return f'src="{data_uri(path)}"'

    html = re.sub(r'src="([^"]+)"', repl, html)
    OUT.write_text(html, encoding="utf-8")

    size_mb = OUT.stat().st_size / 1024 / 1024
    print(f"wrote {OUT.name} — {size_mb:.2f} MB, {len(found)} images inlined")
    for name in sorted(found):
        print(f"  - {name}")


if __name__ == "__main__":
    main()
