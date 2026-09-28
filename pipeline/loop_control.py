#!/usr/bin/env python3
"""Dependency-free A-B and whole-video looping for course player pages.

The injected control uses only the native media API. Whole-video mode sets the
video element's ``loop`` property; A-B mode seeks ``currentTime`` back to the
start at the selected end time. The viewer can type timecodes or press A/B to
capture the current playhead without reaching for the mouse.

This module deliberately mirrors speed_control.py: ``patch_html()`` is usable by
build_site.py (every generated player page), while the CLI patches
already-built pages in place. It also adds restart and play/pause transport
buttons beside the video. Piloted on the AWS AI Practitioner course's Chapter 2
and rolled out to every player there.
"""
import re
import sys
from pathlib import Path


# Present in every patched page and used as the idempotence marker.
MARKER = "id='loop-label'"

# Default cyberdeck cyan, used when a page has no h1 colour to sniff.
DEFAULT_ACCENT = "#27d4ff"

# __ACCENT__ is substituted per page. A token is safer than str.format because
# the JavaScript contains many braces.
BLOCK = r"""<style>
.loopctl{--loop:var(--accent, __ACCENT__);display:flex;align-items:center;
  flex:1 1 100%;gap:9px;flex-wrap:wrap;color:var(--loop);font-size:14px;
  user-select:none;padding-top:2px}
.loopctl .loop-label{font-weight:700}
.loopctl .loop-modes{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.loopctl label{display:flex;align-items:center;gap:4px;white-space:nowrap;cursor:pointer}
.loopctl input[type=radio]{accent-color:var(--loop);cursor:pointer}
.loopctl input[type=text]{font:inherit;color:inherit;background:transparent;
  border:1px solid color-mix(in srgb,var(--loop) 45%,transparent);border-radius:6px;
  width:86px;height:28px;padding:3px 7px;user-select:text}
.loopctl input[type=text]:focus{outline:1px solid var(--loop);border-color:var(--loop)}
.loopctl input[type=text][aria-invalid=true]{border-color:#ff5c72;color:#ff8b9b}
.loopctl input:disabled,.loopctl button:disabled{opacity:.4;cursor:not-allowed}
.loopctl button{font:inherit;color:inherit;background:transparent;
  border:1px solid color-mix(in srgb,var(--loop) 45%,transparent);border-radius:6px;
  height:28px;padding:0 8px;cursor:pointer;line-height:1}
.loopctl button:hover:not(:disabled){border-color:var(--loop);
  background:color-mix(in srgb,var(--loop) 14%,transparent)}
.loopctl #loop-set-a,.loopctl #loop-set-b{color:#cfd8e3;background:#0e1a2c}
.loopctl #loop-set-a:hover:not(:disabled),.loopctl #loop-set-b:hover:not(:disabled){background:#13233a}
.loopctl #loop-reset,.loopctl #loop-stop{color:#8c99a8;background:#0a0e15;
  border-color:#5a6678;border-style:dashed}
.loopctl #loop-reset:hover:not(:disabled),.loopctl #loop-stop:hover:not(:disabled){
  color:#cfd8e3;background:#141a26;border-color:#8c99a8}
.loopctl #loop-stop[hidden]{display:none}
.loopctl .loop-feedback{display:flex;align-items:center;gap:9px;flex:1 1 250px;min-width:220px}
.loopctl .loop-status{color:color-mix(in srgb,var(--loop) 72%,#cfd8e3);font-size:12px}
.video-action{font:inherit;color:#8c99a8;background:#0a0e15;border:1px dashed #5a6678;
  border-radius:7px;width:36px;height:35px;padding:0;display:inline-flex;align-items:center;
  justify-content:center;cursor:pointer;line-height:1;white-space:nowrap}
.video-action:hover{color:#cfd8e3;background:#141a26;border-color:#8c99a8}
.video-actions{display:flex;align-items:center;justify-content:center;gap:6px;
  flex:1 1 320px;min-width:240px}
.video-actions .upnext{flex:0 1 auto;min-width:0}
@media(max-width:700px){.loopctl .loop-feedback{flex-basis:100%}}
</style>
<div class='loopctl' role='group' aria-labelledby='loop-label'>
  <span class='loop-label' id='loop-label'>Loop</span>
  <span class='loop-modes' role='radiogroup' aria-label='Loop mode'>
    <label><input type='radio' name='cw-loop' id='loop-off' value='off' checked>Off</label>
    <label><input type='radio' name='cw-loop' id='loop-ab' value='ab'>A&ndash;B</label>
    <label><input type='radio' name='cw-loop' id='loop-all' value='all'>Entire video</label>
  </span>
  <label>Start <input type='text' id='loop-start' value='0:00' inputmode='decimal'
    autocomplete='off' spellcheck='false' aria-label='Loop start time'></label>
  <button id='loop-set-a' type='button' aria-label='Set loop start to current position'>Set A</button>
  <button id='loop-reset' type='button' aria-label='Reset A-B range and continue playback'>&#8634; Reset</button>
  <label>End <input type='text' id='loop-end' value='--:--' inputmode='decimal'
    autocomplete='off' spellcheck='false' aria-label='Loop end time'></label>
  <button id='loop-set-b' type='button' aria-label='Set loop end to current position'>Set B</button>
  <span class='loop-feedback'>
    <span class='loop-status' id='loop-status' role='status' aria-live='polite'>A/B keys capture the playhead</span>
    <button id='loop-stop' type='button' aria-label='Turn looping off' hidden>Off</button>
  </span>
</div>
<script>
(function(){
'use strict';
var V=document.querySelector('video');
if(!V) return;
var START=document.getElementById('loop-start'), END=document.getElementById('loop-end');
var STATUS=document.getElementById('loop-status');
var RESET=document.getElementById('loop-reset');
var STOP=document.getElementById('loop-stop');
var UPNEXT=document.querySelector('.upnext'), ACTIONS=null, RESTART=null, PLAYBACK=null;
var MODES={off:document.getElementById('loop-off'),ab:document.getElementById('loop-ab'),all:document.getElementById('loop-all')};
var KEY='cw_loop:'+location.pathname, mode='off', start=0, end=NaN, ready=false;
var saved=null, framePending=false;

if(UPNEXT){
  ACTIONS=document.createElement('span');ACTIONS.className='video-actions';
  RESTART=document.createElement('button');
  RESTART.id='video-restart';RESTART.className='video-action';RESTART.type='button';
  RESTART.textContent='↺';RESTART.setAttribute('aria-label','Restart video from the beginning');
  RESTART.title='Restart video from the beginning';
  PLAYBACK=document.createElement('button');
  PLAYBACK.id='video-playback';PLAYBACK.className='video-action';PLAYBACK.type='button';
  UPNEXT.parentNode.insertBefore(ACTIONS,UPNEXT);
  ACTIONS.appendChild(RESTART);ACTIONS.appendChild(UPNEXT);ACTIONS.appendChild(PLAYBACK);
}

function finite(n){return typeof n==='number'&&Number.isFinite(n)}
function clamp(n,lo,hi){return Math.min(hi,Math.max(lo,n))}
function formatTime(n){
  if(!finite(n)) return '--:--';
  var ticks=Math.max(0,Math.round(n*10)), tenth=ticks%10, seconds=Math.floor(ticks/10);
  var s=seconds%60, minutes=Math.floor(seconds/60), m=minutes%60, h=Math.floor(minutes/60);
  var tail=(s<10?'0':'')+s+(tenth?'.'+tenth:'');
  return h ? h+':'+(m<10?'0':'')+m+':'+tail : minutes+':'+tail;
}
function parseTime(raw){
  var text=String(raw).trim();
  if(!/^\d+(?:\.\d+)?$/.test(text)&&!/^\d+:\d{1,2}(?::\d{1,2})?(?:\.\d+)?$/.test(text)) return NaN;
  var p=text.split(':').map(Number), n;
  if(p.some(function(x){return !finite(x)})) return NaN;
  if(p.length===1) n=p[0];
  else if(p.length===2){if(p[1]>=60)return NaN;n=p[0]*60+p[1];}
  else {if(p[1]>=60||p[2]>=60)return NaN;n=p[0]*3600+p[1]*60+p[2];}
  return n;
}
function tell(text,error){STATUS.textContent=text;STATUS.style.color=error?'#ff8b9b':''}
function setInvalid(el,bad){el.setAttribute('aria-invalid',bad?'true':'false')}
function validRange(a,b){return ready&&finite(a)&&finite(b)&&a>=0&&a<b&&b<=V.duration+.11}
function normalizeFields(){START.value=formatTime(start);END.value=formatTime(end)}
function syncPlayback(){
  if(!PLAYBACK) return;
  var willPlay=V.paused||V.ended;
  var label=willPlay?'Play video':'Pause video';
  PLAYBACK.textContent=willPlay?'▶':'⏸︎';
  PLAYBACK.setAttribute('aria-label',label);PLAYBACK.title=label;
}
function readSaved(){
  try{
    var raw=localStorage.getItem(KEY);
    if(!raw) return null;
    var value=JSON.parse(raw);
    if(!value||!['off','ab','all'].includes(value.mode)) return null;
    return {mode:value.mode,start:Number(value.start),end:Number(value.end)};
  }catch(e){return null}
}
function save(){
  if(!ready) return;
  try{localStorage.setItem(KEY,JSON.stringify({mode:mode,start:start,end:end}))}catch(e){}
}
function syncDisabled(){
  var disabled=mode==='all';
  START.disabled=END.disabled=disabled;
  document.getElementById('loop-set-a').disabled=disabled;
  document.getElementById('loop-set-b').disabled=disabled;
  STOP.hidden=mode==='off';
}
function announce(){
  if(mode==='all') tell('Looping the entire video',false);
  else if(mode==='ab') tell('Looping '+formatTime(start)+' – '+formatTime(end),false);
  else tell('A/B keys capture the playhead',false);
}
function checkBoundary(at){
  if(mode!=='ab'||!validRange(start,end)) return;
  if(at<start-.05||at>=end){V.currentTime=start;}
}
function onFrame(now,metadata){
  framePending=false;
  if(mode!=='ab') return;
  checkBoundary(metadata&&finite(metadata.mediaTime)?metadata.mediaTime:V.currentTime);
  scheduleFrame();
}
function scheduleFrame(){
  if(mode==='ab'&&!framePending&&!V.paused&&!V.ended&&typeof V.requestVideoFrameCallback==='function'){
    framePending=true;
    V.requestVideoFrameCallback(onFrame);
  }
}
function setMode(next,persist){
  if(next==='ab'&&!validRange(start,end)){
    tell('Start must be before End and inside the video',true);
    MODES[mode].checked=true;
    return false;
  }
  mode=next;
  MODES[mode].checked=true;
  V.loop=mode==='all';
  syncDisabled();
  if(mode==='ab'){
    checkBoundary(V.currentTime);
    scheduleFrame();
  }
  announce();
  if(persist!==false) save();
  return true;
}
function commitFields(){
  if(!ready) return false;
  var a=parseTime(START.value), b=parseTime(END.value);
  if(finite(a)&&Math.abs(a-V.duration)<.11) a=V.duration;
  if(finite(b)&&Math.abs(b-V.duration)<.11) b=V.duration;
  var aBad=!finite(a)||a<0||a>=V.duration||!(a<b);
  var bBad=!finite(b)||b<=0||b>V.duration+.11||!(a<b);
  setInvalid(START,aBad);setInvalid(END,bBad);
  if(aBad||bBad){tell('Use SS, M:SS, or H:MM:SS; Start must be before End',true);return false;}
  start=clamp(a,0,V.duration);end=clamp(b,0,V.duration);
  normalizeFields();save();
  if(mode==='ab') checkBoundary(V.currentTime);
  announce();
  return true;
}
function captureA(){
  if(!ready) return;
  var at=clamp(V.currentTime,0,V.duration);
  if(at>=V.duration){tell('Move before the end to set Start',true);return;}
  start=at;
  if(!finite(end)||end<=start) end=V.duration;
  setInvalid(START,false);setInvalid(END,false);normalizeFields();setMode('ab');
}
function captureB(){
  if(!ready) return;
  var at=clamp(V.currentTime,0,V.duration);
  if(at<=start){tell('End must be after Start',true);return;}
  end=at;
  setInvalid(START,false);setInvalid(END,false);normalizeFields();setMode('ab');
}
function resetLoop(){
  if(!ready) return;
  start=0;end=V.duration;
  setInvalid(START,false);setInvalid(END,false);normalizeFields();setMode('off');
  tell('Loop reset and off; set A for the next passage',false);
  V.play().catch(function(){});
}
function stopLoop(){
  if(!ready) return;
  setMode('off');
}
function restartVideo(){
  V.currentTime=mode==='ab'?start:0;
  V.play().catch(syncPlayback);
}
function togglePlayback(){
  if(V.paused||V.ended) V.play().then(syncPlayback).catch(syncPlayback);
  else {V.pause();syncPlayback();}
}

saved=readSaved();
if(saved&&saved.mode==='all'){mode='all';V.loop=true;MODES.all.checked=true;syncDisabled();}
Object.keys(MODES).forEach(function(name){MODES[name].addEventListener('change',function(){if(this.checked)setMode(name);});});
START.addEventListener('change',commitFields);END.addEventListener('change',commitFields);
[START,END].forEach(function(el){el.addEventListener('keydown',function(e){if(e.key==='Enter'){e.preventDefault();commitFields();el.blur();}});});
document.getElementById('loop-set-a').addEventListener('click',captureA);
document.getElementById('loop-set-b').addEventListener('click',captureB);
RESET.addEventListener('click',resetLoop);
STOP.addEventListener('click',stopLoop);
if(RESTART) RESTART.addEventListener('click',restartVideo);
if(PLAYBACK) PLAYBACK.addEventListener('click',togglePlayback);
document.addEventListener('keydown',function(e){
  if(e.metaKey||e.ctrlKey||e.altKey||e.repeat) return;
  if(e.target&&e.target.matches&&e.target.matches('input,textarea,select,button,[contenteditable=true]')) return;
  var key=e.key.toLowerCase();
  if(key==='a') captureA(); else if(key==='b') captureB(); else return;
  e.preventDefault();
});
V.addEventListener('play',function(){scheduleFrame();syncPlayback();});
V.addEventListener('pause',syncPlayback);
V.addEventListener('ended',syncPlayback);
V.addEventListener('timeupdate',function(){
  if(typeof V.requestVideoFrameCallback!=='function') checkBoundary(V.currentTime);
});
V.addEventListener('seeked',function(){if(mode==='ab')checkBoundary(V.currentTime);});
// Capture phase runs before the player's existing target-level autoplay-next
// listener. This matters when B equals the true end of the file.
document.addEventListener('ended',function(e){
  if(e.target!==V||mode==='off') return;
  e.stopImmediatePropagation();
  V.currentTime=mode==='ab'?start:0;
  V.play().catch(function(){});
},true);
function initialize(){
  if(ready) return;
  if(!finite(V.duration)||V.duration<=0){tell('Looping is unavailable for this video',true);return;}
  ready=true;start=0;end=V.duration;mode='off';
  if(saved){
    var good=finite(saved.start)&&finite(saved.end)&&saved.start>=0&&saved.start<saved.end&&saved.end<=V.duration+.11;
    if(good){start=clamp(saved.start,0,V.duration);end=clamp(saved.end,0,V.duration);mode=saved.mode;}
    else if(saved.mode==='all'){mode='all';}
  }
  normalizeFields();setInvalid(START,false);setInvalid(END,false);setMode(mode,false);
}
V.addEventListener('loadedmetadata',initialize);
if(V.readyState>=1) initialize();
syncPlayback();
})();
</script>
"""


ANCHORS = ("</div>\n<footer", "</body>")
_ACCENT_RE = re.compile(r"h1\{color:(#[0-9a-fA-F]{6})")


def _accent(page):
    """Return the page's accent so the control matches the course theme."""
    match = _ACCENT_RE.search(page)
    return match.group(1) if match else DEFAULT_ACCENT


def patch_html(page):
    """Inject the loop control once, leaving non-player pages unchanged."""
    if MARKER in page or "<video" not in page:
        return page
    block = BLOCK.replace("__ACCENT__", _accent(page))
    for anchor in ANCHORS:
        index = page.find(anchor)
        if index != -1:
            return page[:index] + block + page[index:]
    return page


def patch_file(path, backup=True):
    """Patch one HTML file in place. Return True only when it changed."""
    source = path.read_text(encoding="utf-8")
    output = patch_html(source)
    if output == source:
        return False
    if backup:
        backup_path = path.with_suffix(path.suffix + ".bak.preloop")
        if not backup_path.exists():
            backup_path.write_text(source, encoding="utf-8")
    path.write_text(output, encoding="utf-8")
    return True


def main(argv):
    backup = "--no-backup" not in argv
    argv = [arg for arg in argv if arg != "--no-backup"]
    if not argv:
        print(
            "usage: loop_control.py [--no-backup] <dir-or-file> [...]"
            "   (idempotent, in place)"
        )
        return 2
    patched = skipped = nonplayer = failed = 0
    for arg in argv:
        path = Path(arg)
        files = sorted(path.rglob("*.html")) if path.is_dir() else [path]
        for html_file in files:
            try:
                source = html_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                print(f"  !! unreadable {html_file}: {exc}")
                failed += 1
                continue
            if "<video" not in source:
                nonplayer += 1
            elif MARKER in source:
                skipped += 1
            elif patch_file(html_file, backup=backup):
                patched += 1
            else:
                print(f"  !! no anchor, NOT patched: {html_file}")
                failed += 1
    print(
        f"patched {patched}, already-had-it {skipped}, "
        f"non-player {nonplayer}, FAILED {failed}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
