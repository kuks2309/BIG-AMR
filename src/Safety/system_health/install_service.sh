#!/usr/bin/env bash
# systemd 유닛 설치 스크립트 — 샘플러(수집) + 대시보드(열람).
#
# 사용자가 명시적으로 실행할 때만 설치한다 — 코드 배포만으로 상주 서비스가 생기지 않게 하기
# 위해서다(ADR 2026-07-28 §Decision 7).
#
# 두 유닛은 **서로 의존하지 않는다**. 대시보드가 죽어도 기록은 계속되고, 샘플러가 죽어도
# 지금까지의 기록은 볼 수 있어야 하기 때문이다.
#
# 사용:
#   ./install_service.sh                    # 무엇을 할지 보여주기만 한다(dry-run)
#   ./install_service.sh --apply            # 둘 다 설치·기동
#   ./install_service.sh --apply sampler    # 샘플러만
#   ./install_service.sh --apply webview    # 대시보드만
#   ./install_service.sh --remove [대상]    # 제거 (ADR 2026-07-28 §Rollback)
#   ./install_service.sh --status           # 현재 상태
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 저장소 경로는 **스크립트 위치에서 유도**한다(HERE = <repo>/src/Safety/system_health).
# 하드코딩하면 다른 PC 로 이식한 사본이 원본 장비의 경로를 향한다.
REPO="$(cd "${HERE}/../../.." && pwd)"
LOG_DIR="${REPO}/Log/health"
CONFIG="${REPO}/config/system_health/thresholds.json"
# 유닛은 이 계정으로 돈다. 경로만 맞추고 계정을 그대로 두면 다른 PC 에서 기동하지 못한다.
RUN_USER="$(id -un)"
RUN_GROUP="$(id -gn)"

# 장비별 서비스 설정(선택). 없으면 기본값을 쓴다. 임계값 파일과 같은 자리에 둔다.
SERVICE_ENV="${REPO}/config/system_health/service.env"
# shellcheck source=/dev/null
[ -f "${SERVICE_ENV}" ] && . "${SERVICE_ENV}"
# 대시보드 포트. 장비에 따라 8770 을 다른 서비스가 이미 쓰고 있어 값을 밖으로 뺀다.
HEALTH_PORT="${HEALTH_PORT:-8770}"

SAMPLER_UNIT="amr-health-sampler.service"
WEBVIEW_UNIT="amr-health-webview.service"

MODE="${1:-}"
TARGET="${2:-both}"

units_for_target() {
  case "$1" in
    sampler) echo "${SAMPLER_UNIT}" ;;
    webview) echo "${WEBVIEW_UNIT}" ;;
    both|"") echo "${SAMPLER_UNIT} ${WEBVIEW_UNIT}" ;;
    *) echo "알 수 없는 대상: $1 (sampler|webview|both)" >&2; exit 1 ;;
  esac
}

# 유닛 파일은 자리표시자(@REPO@·@USER@·@GROUP@)를 가진 템플릿이다. 설치 시점에 이 장비의
# 실제 값으로 치환한다 — 소스의 .service 를 systemctl 에 그대로 넣으면 동작하지 않는다.
render_unit() {
  sed -e "s|@REPO@|${REPO}|g" -e "s|@USER@|${RUN_USER}|g" -e "s|@GROUP@|${RUN_GROUP}|g" \
      -e "s|@PORT@|${HEALTH_PORT}|g" "$1"
}

# 이미 쓰이는 포트에 설치하면 대시보드가 기동 직후 Address already in use 로 죽는다.
# 차단하지는 않는다 — 우리 유닛이 이미 그 포트로 돌고 있는 재설치도 정상 경로다.
warn_if_port_taken() {
  if ss -ltn 2>/dev/null | grep -q ":${HEALTH_PORT} "; then
    echo "⚠ 포트 ${HEALTH_PORT} 가 이미 LISTEN 중이다 — 다른 서비스면 대시보드가 뜨지 못한다." >&2
    echo "  점유자 확인: ss -ltnp | grep ${HEALTH_PORT}" >&2
    echo "  포트 변경: ${SERVICE_ENV} 에 HEALTH_PORT=<포트> 를 적고 --apply 재실행" >&2
  fi
}

install_unit() {
  local unit="$1" src="${HERE}/systemd/$1" dst="/etc/systemd/system/$1"
  [ -f "${src}" ] || { echo "유닛 파일 없음: ${src}" >&2; exit 1; }
  render_unit "${src}" | sudo install -m 0644 /dev/stdin "${dst}"
  echo "설치: ${dst}  (REPO=${REPO} · User=${RUN_USER})"
}

case "${MODE}" in
  --apply)
    UNITS="$(units_for_target "${TARGET}")"
    case "${UNITS}" in *"${WEBVIEW_UNIT}"*) warn_if_port_taken ;; esac
    mkdir -p "${LOG_DIR}"
    # 임계값 파일이 없으면 기본값으로 만든다. 있으면 **덮어쓰지 않는다** —
    # 사용자가 고쳐 둔 값을 재설치가 되돌리면 안 된다.
    if [ -f "${CONFIG}" ]; then
      echo "임계값 파일 유지(덮어쓰지 않음): ${CONFIG}"
    else
      PYTHONPATH="${HERE}" python3 -m system_health.sampler --write-thresholds "${CONFIG}"
    fi
    for u in ${UNITS}; do install_unit "${u}"; done
    sudo systemctl daemon-reload
    for u in ${UNITS}; do sudo systemctl enable --now "${u}"; done
    for u in ${UNITS}; do sudo systemctl --no-pager --lines=3 status "${u}" || true; done
    ;;
  --remove)
    for u in $(units_for_target "${TARGET}"); do
      sudo systemctl disable --now "${u}" || true
      sudo rm -f "/etc/systemd/system/${u}"
      echo "제거: ${u}"
    done
    sudo systemctl daemon-reload
    echo "로그·임계값 파일은 지우지 않았다: ${LOG_DIR} · ${CONFIG}"
    ;;
  --status)
    for u in ${SAMPLER_UNIT} ${WEBVIEW_UNIT}; do
      # `is-active`/`is-enabled` 는 미설치 유닛에도 값을 찍고 **비-0 을 반환**한다.
      # `|| echo …` 를 붙이면 두 줄이 겹쳐 나오므로 `|| true` 로 두고 빈 값만 보정한다.
      act="$(systemctl is-active "${u}" 2>/dev/null || true)"
      ena="$(systemctl is-enabled "${u}" 2>/dev/null || true)"
      printf "%-32s %s / %s\n" "${u}" "${act:-unknown}" "${ena:-not-installed}"
    done
    ;;
  *)
    cat <<EOF
[dry-run] 실제로는 아무것도 바꾸지 않았다.

--apply [sampler|webview|both] 를 주면:
  1. mkdir -p ${LOG_DIR}
  2. 임계값 파일 생성(없을 때만 — 기존 값은 덮어쓰지 않음): ${CONFIG}
  3. 유닛 설치 -> /etc/systemd/system/
       ${SAMPLER_UNIT}  (수집, 5초 주기)
       ${WEBVIEW_UNIT}  (대시보드, **127.0.0.1 전용**, 포트 ${HEALTH_PORT})
  4. systemctl daemon-reload
  5. systemctl enable --now (부팅 시 자동 기동)

대시보드는 **로컬 전용**이다 — 인증이 없어 루프백에만 바인드하고,
IPAddressDeny=any 로 커널에서도 외부 접속을 막는다.
다른 PC 에서 보려면 SSH 터널을 쓴다:
  ssh -L ${HEALTH_PORT}:127.0.0.1:${HEALTH_PORT} ${RUN_USER}@<이 장비>
  그 뒤 브라우저에서 http://127.0.0.1:${HEALTH_PORT}/

포트를 바꾸려면 ${SERVICE_ENV} 에 HEALTH_PORT=<포트> 를 적고 --apply 를 다시 실행한다.

임계값을 바꾸려면 ${CONFIG} 를 편집한 뒤:
  sudo systemctl restart ${SAMPLER_UNIT}

--status  현재 상태 조회
--remove [sampler|webview|both]  되돌리기(로그·임계값은 보존)
EOF
    ;;
esac
