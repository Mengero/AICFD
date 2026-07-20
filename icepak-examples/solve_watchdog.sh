#!/bin/bash
# solve_watchdog.sh -- an INDEPENDENT, ALARMING watchdog for an Icepak batchsolve.
#
# Why: MRF/Fluent solves can hang (MPI deadlock), and a long sweep then "fails"
# silently overnight. An in-line watchdog is useless if it (1) only writes a log
# line nobody tails, and (2) runs in the launching shell so session-end SIGHUP
# kills it too. This one fixes both:
#   * it ALARMS (sentinel file + notify-send + $ICEPAK_PING_CMD + loud stderr);
#   * it is meant to run DETACHED so it survives the launching session. Start it
#     with setsid so SIGHUP can't kill it:
#
#       setsid nohup ./solve_watchdog.sh \
#           --log out/solve_case1.log \
#           --pattern "batchsolve.*case1" \
#           --label case1 --stall 1080 --hardcap 8400 \
#           >> out/watchdog_case1.log 2>&1 &
#
# Monitor-only by default (does NOT kill the solver). Add --kill to kill a
# stalled/over-cap solve. Watches the solve LOG (growth + "Normal completion")
# and the solver PROCESS (alive?), independently of who launched it.
#
# Exit / alarm reasons: 0 completed | 2 crash (process gone, no completion)
#                        3 stall     | 4 hardcap
set -u
INTERVAL=60; STALL=1080; HARDCAP=0; KILL=0; LABEL="solve"; LOG=""; PID=""; PATTERN=""
while [ $# -gt 0 ]; do case "$1" in
  --log) LOG="$2"; shift 2;; --pid) PID="$2"; shift 2;; --pattern) PATTERN="$2"; shift 2;;
  --label) LABEL="$2"; shift 2;; --stall) STALL="$2"; shift 2;; --hardcap) HARDCAP="$2"; shift 2;;
  --interval) INTERVAL="$2"; shift 2;; --kill) KILL=1; shift;; *) echo "unknown arg $1"; exit 64;; esac; done
[ -z "$LOG" ] && { echo "need --log"; exit 64; }
ALARM="${LOG}.ALARM"

alarm() {  # $1=severity $2=message
  local sev="$1" msg="$2" ts; ts=$(date '+%F %T')
  { echo; echo "############################################################";
    echo "# WATCHDOG ALARM [$sev] $LABEL  $ts";
    echo "# $msg";
    echo "# log: $LOG";
    echo "############################################################"; } >&2
  printf '[%s] %s: %s\n' "$ts" "$sev" "$msg" >> "$ALARM"
  command -v notify-send >/dev/null 2>&1 && notify-send "Icepak watchdog [$sev]: $LABEL" "$msg" 2>/dev/null
  [ -n "${ICEPAK_PING_CMD:-}" ] && $ICEPAK_PING_CMD "Icepak watchdog [$sev] $LABEL: $msg" 2>/dev/null
}

alive() {  # is the solver still running?
  if [ -n "$PID" ]; then kill -0 "$PID" 2>/dev/null; return $?; fi
  [ -n "$PATTERN" ] && pgrep -f "$PATTERN" >/dev/null 2>&1
}

kill_solvers() {
  if [ -n "$PID" ]; then kill -9 "$PID" 2>/dev/null; fi
  [ -n "$PATTERN" ] && for p in $(pgrep -f "$PATTERN"); do kill -9 "$p" 2>/dev/null; done
}

echo "[$(date '+%F %T')] watchdog START label=$LABEL log=$LOG stall=${STALL}s hardcap=${HARDCAP}s kill=$KILL"
last=-1; stall=0; el=0
while true; do
  sleep "$INTERVAL"; el=$((el+INTERVAL))
  if grep -qa "Normal completion" "$LOG" 2>/dev/null; then
    alarm OK "solve completed normally after ${el}s"; exit 0
  fi
  sz=$(stat -c%s "$LOG" 2>/dev/null || echo 0)
  if [ "$sz" -eq "$last" ]; then stall=$((stall+INTERVAL)); else stall=0; last=$sz; fi
  if ! alive; then
    grep -qa "Normal completion" "$LOG" 2>/dev/null && exit 0
    alarm CRASH "solver process is gone but log has no 'Normal completion' (crashed or was killed) after ${el}s"
    exit 2
  fi
  if [ "$stall" -ge "$STALL" ]; then
    alarm STALL "log has not grown for ${stall}s (likely MPI/Fluent deadlock)"
    [ "$KILL" -eq 1 ] && { kill_solvers; alarm STALL "killed stalled solver"; }
    exit 3
  fi
  if [ "$HARDCAP" -gt 0 ] && [ "$el" -ge "$HARDCAP" ]; then
    alarm HARDCAP "exceeded hard cap ${HARDCAP}s"
    [ "$KILL" -eq 1 ] && { kill_solvers; alarm HARDCAP "killed over-cap solver"; }
    exit 4
  fi
done
