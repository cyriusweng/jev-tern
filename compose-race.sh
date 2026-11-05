#!/bin/zsh
# compose-race.sh TJ TB — side-by-side race video from race-left/ and race-right/.
# TJ: jev-tern elapsed s; TB: browser-use wall s. Cap 180 s; a capped loser keeps
# its last frame with a "still running — finished at M:SS" stamp.
set -e
TJ=${1:?jev seconds}; TB=${2:?bu seconds}
CAP=180
FJ=$(printf %.0f $(echo "$TJ*25" | bc))
FB=$(printf %.0f $(echo "$TB*25" | bc))
CAPF=$(printf %.0f $(echo "$CAP*25" | bc))
EFFECTIVE=$(( TB < CAP ? TB : CAP ))
TOT=$(printf %.2f $(echo "$EFFECTIVE + 2.5" | bc))
LTPAD=$(printf %.2f $(echo "$TOT - $TJ" | bc))
RTPAD=$(printf %.2f $(echo "$TOT - $EFFECTIVE" | bc))
RTRIM=$EFFECTIVE
LEFT=race-left/right.mp4
RIGHT=race-right/right.mp4
MENLO=/System/Library/Fonts/Menlo.ttc


rm -rf race-overlay && mkdir race-overlay
bench/.venv/bin/python bench/render-overlay.py "$TJ" "$TB" "$TOT"

ffmpeg -y -v error \
  -i "$LEFT" -i "$RIGHT" -framerate 25 -i race-overlay/overlay-%05d.png \
  -filter_complex "
  [0:v]fps=25,scale=1200:1000,setsar=1,tpad=stop_mode=clone:stop_duration=${LTPAD}[L];
  [1:v]fps=25,scale=1200:1000,setsar=1,trim=duration=${RTRIM},tpad=stop_mode=clone:stop_duration=${RTPAD}[R];
  [L][R]hstack=inputs=2[base];
  [base][2:v]overlay=0:0:shortest=1[v]" \
  -map "[v]" -t "$TOT" -c:v libx264 -pix_fmt yuv420p -movflags +faststart -crf 22 docs/race.mp4

ffprobe -v error -select_streams v -show_entries stream=width,height,r_frame_rate -show_entries format=duration,size -of default=nw=1 docs/race.mp4
