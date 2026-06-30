#!/usr/bin/env python3
"""Render a Cyberdeck HTML slide to a PNG via headless Chrome.

    render_slides.py <slide.html> <out.png> [width] [height]

Renders at 2x device scale (so a 1280x720 slide -> 2560x1440 PNG) for a crisp
source that the Ken Burns 5K upscale can push into without softening.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Below this auto-fit scale a slide is too dense (content > ~1.4x the safe area):
# scaling keeps it from overhanging, but the text gets small — warn so the slide
# gets split/trimmed rather than silently shrunk into illegibility.
FIT_WARN_BELOW = 0.72

# Auto-fit: injected before screenshot. Wraps the in-flow slide content (leaving
# absolutely-positioned chrome like <footer> alone) and scales it down with a CSS
# transform so an over-stuffed slide shrinks to fit the 1280x720 safe area instead
# of overhanging/clipping. No-op (scale 1) when content already fits. The chosen
# scale is written to the document title as "FIT:<scale>" so the renderer can warn
# when a slide had to shrink a lot (a signal the slide is too dense).
FIT_SCRIPT = """
<script>
(function(){
  function fit(){
    var b=document.body, W=1280, H=720, cs=getComputedStyle(b);
    var availW=W-(parseFloat(cs.paddingLeft)||0)-(parseFloat(cs.paddingRight)||0);
    var availH=H-(parseFloat(cs.paddingTop)||0)-(parseFloat(cs.paddingBottom)||0);
    var kids=[].slice.call(b.children).filter(function(el){
      return getComputedStyle(el).position!=='absolute';
    });
    if(!kids.length){document.title='FIT:1.000';return;}
    var wrap=document.createElement('div');
    wrap.style.width='100%';
    kids.forEach(function(el){wrap.appendChild(el);});
    b.insertBefore(wrap,b.firstChild);
    var s=Math.min(1, availW/wrap.scrollWidth, availH/wrap.scrollHeight);
    if(s<1){wrap.style.transformOrigin='center center';wrap.style.transform='scale('+s+')';}
    document.title='FIT:'+s.toFixed(3);
  }
  if(document.readyState==='complete') fit(); else window.addEventListener('load',fit);
})();
</script>
"""


def _find_chrome() -> str:
    """Locate a Chromium-family browser. Override with the CHROME env var."""
    env = os.environ.get("CHROME")
    if env:
        return env
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
        "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",  # Linux (PATH)
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    for c in candidates:
        if os.path.isabs(c):
            if os.path.exists(c):
                return c
        elif shutil.which(c):
            return shutil.which(c)
    # Fall back to the macOS default; the run will raise a clear error if absent.
    return candidates[0]


CHROME = _find_chrome()


def render(html: Path, out: Path, w: int = 1280, h: int = 720):
    out.parent.mkdir(parents=True, exist_ok=True)

    # Inject the auto-fit script into a temp copy alongside the original, so the
    # relative ../../../pipeline/slides.css link still resolves. Screenshot the
    # temp; clean it up afterwards.
    src = html.read_text(encoding="utf-8")
    if "</body>" in src:
        fitted = src.replace("</body>", FIT_SCRIPT + "</body>", 1)
    else:
        fitted = src + FIT_SCRIPT
    fd, tmp_name = tempfile.mkstemp(suffix=".html", prefix=".fit-", dir=str(html.parent))
    tmp = Path(tmp_name)
    try:
        os.write(fd, fitted.encode("utf-8"))
        os.close(fd)
        cmd = [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=2",
            f"--window-size={w},{h}",
            f"--screenshot={out}",
            tmp.resolve().as_uri(),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Catch over-dense slides: the injected script recorded the chosen scale in
        # the document title. Read it back and warn if it had to shrink hard.
        try:
            dom = subprocess.run(
                [CHROME, "--headless=new", "--disable-gpu", "--dump-dom", tmp.resolve().as_uri()],
                capture_output=True, text=True, timeout=30,
            ).stdout
            m = re.search(r"FIT:([0-9.]+)", dom)
            if m and float(m.group(1)) < FIT_WARN_BELOW:
                print(
                    f"[render_slides] WARNING: {html.name} auto-fit to {m.group(1)} "
                    f"(< {FIT_WARN_BELOW}) — slide is too dense; split or trim it.",
                    file=sys.stderr,
                )
        except Exception:
            pass
    finally:
        tmp.unlink(missing_ok=True)
    if not out.exists():
        raise RuntimeError(f"Chrome did not produce {out}")
    return out


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    html = Path(sys.argv[1])
    out = Path(sys.argv[2])
    w = int(sys.argv[3]) if len(sys.argv) > 3 else 1280
    h = int(sys.argv[4]) if len(sys.argv) > 4 else 720
    print(render(html, out, w, h))


if __name__ == "__main__":
    main()
