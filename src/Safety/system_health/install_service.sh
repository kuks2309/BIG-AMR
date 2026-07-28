#!/usr/bin/env bash
# amr-health-sampler.service 설치 스크립트.
#
# 사용자가 명시적으로 실행할 때만 systemd 유닛을 설치한다 — 코드 배포만으로 상주 서비스가
# 생기지 않게 하기 위해서다(ADR 2026-07-28 §Decision 7).
#
# 사용:
#   ./install_service.sh            # 무엇을 할지 보여주기만 한다(dry-run)
#   ./install_service.sh --apply    # 실제로 설치·기동
#   ./install_service.sh --remove   # 제거 (ADR §Rollback)
set -euo pipefail

UNIT_NAME="amr-health-sampler.service"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_UNIT="${HERE}/systemd/${UNIT_NAME}"
DST_UNIT="/etc/systemd/system/${UNIT_NAME}"
LOG_DIR="/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Log/health"
CONFIG="/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/config/system_health/thresholds.json"

MODE="${1:-}"

case "${MODE}" in
  --apply)
    [ -f "${SRC_UNIT}" ] || { echo "유닛 파일 없음: ${SRC_UNIT}" >&2; exit 1; }
    mkdir -p "${LOG_DIR}"
    # 임계값 파일이 없으면 기본값으로 만든다. 있으면 **덮어쓰지 않는다** —
    # 사용자가 고쳐 둔 값을 재설치가 되돌리면 안 된다.
    if [ -f "${CONFIG}" ]; then
      echo "임계값 파일 유지(덮어쓰지 않음): ${CONFIG}"
    else
      PYTHONPATH="${HERE}" python3 -m system_health.sampler --write-thresholds "${CONFIG}"
    fi
    sudo install -m 0644 "${SRC_UNIT}" "${DST_UNIT}"
    sudo systemctl daemon-reload
    sudo systemctl enable --now "${UNIT_NAME}"
    sudo systemctl --no-pager status "${UNIT_NAME}" || true
    ;;
  --remove)
    sudo systemctl disable --now "${UNIT_NAME}" || true
    sudo rm -f "${DST_UNIT}"
    sudo systemctl daemon-reload
    echo "제거 완료. 로그는 남아 있다: ${LOG_DIR}"
    ;;
  *)
    cat <<EOF
[dry-run] 실제로는 아무것도 바꾸지 않았다.

--apply 를 주면 다음을 수행한다:
  1. mkdir -p ${LOG_DIR}
  2. 임계값 파일 생성(없을 때만 — 기존 값은 덮어쓰지 않음): ${CONFIG}
  3. install -m 0644 ${SRC_UNIT} -> ${DST_UNIT}
  4. systemctl daemon-reload
  5. systemctl enable --now ${UNIT_NAME}

임계값을 바꾸려면 ${CONFIG} 를 편집한 뒤:
  sudo systemctl restart ${UNIT_NAME}

--remove 를 주면 되돌린다(유닛 정지·비활성화·삭제). 로그·임계값 파일은 지우지 않는다.
EOF
    ;;
esac
