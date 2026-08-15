#!/usr/bin/env bash
# systemd 유닛 설치 — can_relay 드라이버 + 노드 감시자.
#
# 사용자가 명시 실행할 때만 설치한다. 코드 배포만으로 상주 서비스가 생기지 않게 하기
# 위해서다. 구조·규율은 `src/Safety/system_health/install_service.sh` 를 따른다
# (경로 유도 S-G2 · 템플릿 치환 S2 · 0644 설치 S4).
#
# 두 유닛은 **서로 의존하지 않는다** — 감시자가 죽어도 드라이버는 돌고, 드라이버가
# 죽어도 감시자는 그 사건을 기록해야 한다.
#
# ⚠ 드라이버 유닛은 **제어권을 잡지 않는다.** 되살아난 노드는 대기 상태이며, 버스
#   획득은 `~/engage` 호출뿐이다. 그 복귀 판단은 감시자가 기록에 근거해 내린다.
#
# 사용:
#   ./install_service.sh                     # 무엇을 할지 보여주기만 한다(dry-run)
#   ./install_service.sh --apply             # 둘 다 설치·기동
#   ./install_service.sh --apply driver      # 드라이버만
#   ./install_service.sh --apply supervisor  # 감시자만
#   ./install_service.sh --remove [대상]     # 제거 (ADR §Rollback 절차)
#   ./install_service.sh --status            # 현재 상태
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 저장소 경로는 스크립트 위치에서 유도한다(HERE = <repo>/src/Comm/CAN/can_relay → 4단계 위).
# 하드코딩하면 다른 PC 로 이식한 사본이 원본 장비의 경로를 향한다.
REPO="$(cd "${HERE}/../../../.." && pwd)"
# 유닛은 이 계정으로 돈다. 경로만 맞추고 계정을 그대로 두면 다른 PC 에서 기동하지 못한다.
RUN_USER="$(id -un)"
RUN_GROUP="$(id -gn)"
# 도메인이 다르면 감시자가 드라이버의 진단을 못 본다 — 두 유닛에 같은 값을 박는다.
ROS_DOMAIN="${ROS_DOMAIN_ID:-0}"

DRIVER_UNIT="amr-can-relay.service"
SUPERVISOR_UNIT="amr-can-relay-supervisor.service"
UNIT_DIR="/etc/systemd/system"

MODE="${1:-}"
TARGET="${2:-both}"

units_for_target() {
  case "$1" in
    driver) echo "${DRIVER_UNIT}" ;;
    supervisor) echo "${SUPERVISOR_UNIT}" ;;
    both|"") echo "${DRIVER_UNIT} ${SUPERVISOR_UNIT}" ;;
    *) echo "알 수 없는 대상: $1 (driver|supervisor|both)" >&2; exit 1 ;;
  esac
}

# 유닛 파일은 자리표시자를 가진 템플릿이다. 소스의 .service 를 systemctl 에 그대로
# 넣으면 동작하지 않는다(파일 상단 주석에도 명시).
render_unit() {
  sed -e "s|@REPO@|${REPO}|g" -e "s|@USER@|${RUN_USER}|g" \
      -e "s|@GROUP@|${RUN_GROUP}|g" -e "s|@DOMAIN@|${ROS_DOMAIN}|g" "$1"
}

install_unit() {
  render_unit "${HERE}/systemd/$1" | sudo install -m 0644 /dev/stdin "${UNIT_DIR}/$1"
}

# 오버레이가 없으면 두 유닛 다 기동 직후 죽는다. 차단하지 않고 경고만 한다 —
# 설치 후 빌드하는 순서도 정상 경로다.
warn_if_no_overlay() {
  if [ ! -f "${REPO}/install/setup.bash" ]; then
    echo "⚠ ${REPO}/install/setup.bash 가 없다 — 먼저 빌드할 것:"
    echo "    cd ${REPO} && colcon build --packages-select can_relay --symlink-install"
  fi
}

# 판다 파이썬 라이브러리는 **git 미추적**이라 새 클론·worktree 에는 없다.
# 없으면 노드는 뜨지만 `~/engage` 가 LinkError 로 거부되어 제어권을 잡지 못한다 —
# 상주 서비스로 설치해 놓고 첫 호출에서야 알게 되는 것을 막는다.
warn_if_no_panda_lib() {
  local found=""
  for p in "${REPO}/Tools/docking_field_kit/panda" \
           "${REPO}/Tools/Can_Relay/panda-firmware/python"; do
    [ -d "$p" ] && found="$p" && break
  done
  if [ -z "${found}" ]; then
    echo "⚠ 판다 파이썬 라이브러리가 없다 — 설치해도 제어권을 잡지 못한다."
    echo "  찾은 경로: ${REPO}/Tools/docking_field_kit/panda (또는 panda-firmware/python)"
    echo "  이 라이브러리는 git 미추적이라 새 클론·worktree 에는 딸려오지 않는다."
    echo "  다른 트리에서 복사하거나 심볼릭 링크할 것."
  fi
}

# 같은 드라이브에 배타적인 안전 모델 둘이 붙는 것을 막는다(debt-018).
# can_relay=Seer 공존·판다 경유 / motor_control=Seer 분리·socketcan 직결.
warn_if_conflicting_driver() {
  if pgrep -f 'motor_control' >/dev/null 2>&1; then
    echo "⚠ motor_control 프로세스가 보인다 — can_relay 와 안전 모델이 배타적이다(debt-018)."
    echo "  두 패키지를 동시에 띄우지 말 것."
  fi
}

case "${MODE}" in
  --apply)
    warn_if_no_overlay
    warn_if_no_panda_lib
    warn_if_conflicting_driver
    for u in $(units_for_target "${TARGET}"); do
      echo "설치: ${u}"
      install_unit "${u}"
    done
    sudo systemctl daemon-reload
    for u in $(units_for_target "${TARGET}"); do
      sudo systemctl enable --now "${u}"
      echo "기동: ${u} → $(systemctl is-active "${u}" 2>/dev/null || true)"
    done
    echo
    echo "확인:  systemctl status ${DRIVER_UNIT} ${SUPERVISOR_UNIT}"
    echo "기록:  cat /run/can_relay/state.json"
    echo "판정:  ros2 topic echo /relay_supervisor/status"
    ;;

  --remove)
    for u in $(units_for_target "${TARGET}"); do
      echo "제거: ${u}"
      sudo systemctl disable --now "${u}" 2>/dev/null || true
      sudo rm -f "${UNIT_DIR}/${u}"
    done
    sudo systemctl daemon-reload
    echo "완료 — 상태 기록은 tmpfs 라 재부팅 시 사라진다(/run/can_relay)."
    ;;

  --status)
    for u in ${DRIVER_UNIT} ${SUPERVISOR_UNIT}; do
      printf '%-38s %s\n' "${u}" "$(systemctl is-active "${u}" 2>/dev/null || echo '미설치')"
    done
    if [ -f /run/can_relay/state.json ]; then
      echo; echo "기록:"; cat /run/can_relay/state.json; echo
    fi
    ;;

  *)
    echo "dry-run — 아무것도 설치하지 않는다."
    echo "  저장소    : ${REPO}"
    echo "  계정      : ${RUN_USER}:${RUN_GROUP}"
    echo "  ROS 도메인 : ${ROS_DOMAIN}"
    echo "  유닛      : ${DRIVER_UNIT} · ${SUPERVISOR_UNIT}"
    warn_if_no_overlay
    warn_if_no_panda_lib
    echo
    echo "설치하려면: $0 --apply [driver|supervisor|both]"
    ;;
esac
