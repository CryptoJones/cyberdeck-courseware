#!/usr/bin/env python3
"""Fine-grained playback-speed control for course player pages.

YouTube's "Custom" speed behaviour: 0.25x-2x in 0.05x steps, on a slider with
-/+ nudge buttons and a click-to-reset readout, remembered across sections in
localStorage['cw_rate'] (same idiom as the existing 'cw_autoplay' toggle).
Native <video controls> only offers coarse presets (Chrome 0.25/0.5/.../2,
Safari 0.5-2), which is why this exists at all.

TWO CALLERS, ONE SNIPPET:
  * build_site.py calls patch_html() on each page it generates -> new renders
    are born with the control.
  * `python3 speed_control.py <dir> [...]` patches ALREADY-BUILT pages in place
    -> the courses live on pluto get it without a re-render. Several live
    courses no longer have a source repo at all, so this path is not optional.

The injected block is self-contained (own <style>, own <script>, IIFE-scoped)
and finds the video with querySelector('video') rather than reusing the page's
`_v` handle, so the SAME block works on every markup variant in the wild:
  <video id='v' controls playsinline autoplay>      -- cyberdeck courses
  <video id='lecture' controls preload='metadata'>  -- Contemporary Color
  <video autoplay>                                  -- a stray IntroStats page
"""
import re
import sys
from pathlib import Path

#: Present in every patched page -- the idempotence marker.
MARKER = "id='sr'"

#: Default cyberdeck cyan, used when a page has no h1 colour to sniff.
DEFAULT_ACCENT = "#27d4ff"

# __ACCENT__ is substituted per page. A placeholder token rather than str.format
# because the JS below is full of braces.
BLOCK = """<style>
.spd{display:flex;align-items:center;gap:9px;color:__ACCENT__;font-size:14px;
  white-space:nowrap;user-select:none}
.spd button{font:inherit;color:#cfd8e3;background:#0e1a2c;border:1px solid __ACCENT__44;
  border-radius:6px;width:30px;height:28px;cursor:pointer;line-height:1;padding:0}
.spd button:hover{border-color:__ACCENT__;background:#13233a}
.spd input[type=range]{accent-color:__ACCENT__;width:150px;cursor:pointer;vertical-align:middle}
.spd .rate{min-width:58px;text-align:center;color:#cfd8e3;cursor:pointer;
  border-bottom:1px dotted __ACCENT__88}
.spd .rate:hover{color:__ACCENT__}
</style>
<div class='spd' title='Playback speed &mdash; [ slower, ] faster, \\ reset'>
  <span>Speed</span>
  <button id='sd' type='button' aria-label='Slower'>&minus;</button>
  <input type='range' id='sr' min='0.25' max='2' step='0.05' value='1'
         aria-label='Playback speed'>
  <button id='su' type='button' aria-label='Faster'>+</button>
  <span class='rate' id='sv' title='Click to reset to 1.00x'>1.00&times;</span>
</div>
<script>
(function(){
var V=document.querySelector('video');
if(!V) return;
var R=document.getElementById('sr'), RV=document.getElementById('sv');
// Snap to the 0.05 grid and clamp to YouTube's own 0.25-2 range.
function CL(x){return Math.min(2,Math.max(.25,Math.round(x*20)/20));}
function setRate(x,save){
  x=CL(x); V.playbackRate=x; R.value=x; RV.textContent=x.toFixed(2)+'\\u00d7';
  if(save!==false){try{localStorage.setItem('cw_rate',String(x))}catch(e){}}
}
var r0=1; try{r0=parseFloat(localStorage.getItem('cw_rate'))||1}catch(e){}
setRate(r0,false);
// Re-assert after the element loads -- playbackRate resets when a source attaches.
V.addEventListener('loadedmetadata',function(){setRate(parseFloat(R.value),false)});
// The native speed menu is still there; mirror it instead of fighting it. The
// value-equality guard is what stops this from looping on our own writes.
V.addEventListener('ratechange',function(){
  var x=CL(V.playbackRate);
  if(Math.abs(x-parseFloat(R.value))>1e-9) setRate(x);
});
R.addEventListener('input',function(){setRate(parseFloat(R.value))});
document.getElementById('sd').addEventListener('click',function(){setRate(V.playbackRate-.05)});
document.getElementById('su').addEventListener('click',function(){setRate(V.playbackRate+.05)});
RV.addEventListener('click',function(){setRate(1)});
document.addEventListener('keydown',function(e){
  if(e.metaKey||e.ctrlKey||e.altKey) return;
  if(e.target&&e.target.matches&&e.target.matches('input,textarea,select')) return;
  if(e.key==='[') setRate(V.playbackRate-.05);
  else if(e.key===']') setRate(V.playbackRate+.05);
  else if(e.key==='\\\\') setRate(1);
  else return;
  e.preventDefault();
});
})();
</script>
"""

#: Insertion points, best first. The first lands the control as the last child
#: of the .bar nav strip (which is flex-wrap, so it takes its own row).
ANCHORS = ("</div>\n<footer", "</body>")

_ACCENT_RE = re.compile(r"h1\{color:(#[0-9a-fA-F]{6})")


def _accent(page):
    """The page's own accent, so the control matches each course's colour."""
    m = _ACCENT_RE.search(page)
    return m.group(1) if m else DEFAULT_ACCENT


def patch_html(page):
    """Inject the speed control. Idempotent. Returns the page unchanged if it is
    already patched or has no <video> / no usable anchor."""
    if MARKER in page or "<video" not in page:
        return page
    block = BLOCK.replace("__ACCENT__", _accent(page))
    for anchor in ANCHORS:
        i = page.find(anchor)
        if i != -1:
            return page[:i] + block + page[i:]
    return page


def patch_file(path, backup=True):
    """Patch one file in place. True if it changed."""
    src = path.read_text(encoding="utf-8")
    out = patch_html(src)
    if out == src:
        return False
    if backup:
        bak = path.with_suffix(path.suffix + ".bak.prespeed")
        if not bak.exists():
            bak.write_text(src, encoding="utf-8")
    path.write_text(out, encoding="utf-8")
    return True


def main(argv):
    if not argv:
        print("usage: speed_control.py <dir-or-file> [...]   (idempotent, in place)")
        return 2
    patched = skipped = novideo = failed = 0
    for arg in argv:
        p = Path(arg)
        files = sorted(p.rglob("*.html")) if p.is_dir() else [p]
        for f in files:
            try:
                src = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                print(f"  !! unreadable {f}: {e}")
                failed += 1
                continue
            if "<video" not in src:
                novideo += 1            # index/quiz pages -- not player pages
            elif MARKER in src:
                skipped += 1            # already patched
            elif patch_file(f):
                patched += 1
            else:
                # Has a video but no anchor matched -- do NOT fail silently.
                print(f"  !! no anchor, NOT patched: {f}")
                failed += 1
    print(f"patched {patched}, already-had-it {skipped}, "
          f"non-player {novideo}, FAILED {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
