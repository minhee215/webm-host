#!/bin/bash
# Bootstrap a fresh Linux box (e.g. the Higgsfield sandbox) for rendering:
# deps, latest branch, plates, normalized clips + proxies, tracking data.
set -e
cd "$HOME"
python3 -c "import skia, scipy, cv2, mediapipe" 2>/dev/null || pip install -q --user skia-python scipy opencv-python-headless mediapipe
BR=claude/axcore-promo-video-g3ar0z
if [ -d repo ]; then (cd repo && git fetch -q --depth 1 origin $BR && git reset -q --hard FETCH_HEAD); \
else git clone -q --depth 1 -b $BR https://github.com/minhee215/webm-host repo; fi
cd repo/axcore_promo
git log --oneline | head -1
python3 fetch_plates.py | grep -vc cached || true
python3 prep_clips.py | grep -v cached || true
missing=$(python3 -c "
import json,os
m=json.load(open('assets/clips.json'))['clips']
print(' '.join(n for n,i in m.items() if 'track' in i and not os.path.exists('clips/%s_track.json'%n)))")
[ -n "$missing" ] && python3 track.py clips $missing 2>&1 | grep "frames;" || true
echo SETUP_OK
