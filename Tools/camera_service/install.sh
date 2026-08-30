#!/usr/bin/env bash
# 카메라 서비스 설치 — 유닛 복사 → daemon-reload → 카메라별 인스턴스 enable.
#
#   sudo ./install.sh          # 설치 + 부팅 자동기동 등록 + 즉시 기동
#   sudo ./install.sh --no-start   # 등록만, 지금은 안 띄움
#
# 인스턴스 목록은 공용 로스터(config/camera/camera_common.yaml)에서 읽는다 —
# 카메라를 추가/삭제하면 이 스크립트를 다시 돌리면 된다.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${HERE}/../.." && pwd)}"
UNIT_DIR=/etc/systemd/system
START=1
[[ "${1:-}" == "--no-start" ]] && START=0

if [[ $EUID -ne 0 ]]; then
  echo "root 권한이 필요하다: sudo $0" >&2
  exit 1
fi

# 로스터에서 카메라 이름을 뽑는다(하드코딩 금지 — SSOT 는 yaml).
mapfile -t CAMERAS < <(REPO_ROOT="${REPO_ROOT}" python3 -c "
import sys
sys.path.insert(0, '${HERE}')
from camera_params import load_roster, camera_names, default_config_path
print('\n'.join(camera_names(load_roster(default_config_path('${REPO_ROOT}')))))
")

if [[ ${#CAMERAS[@]} -eq 0 ]]; then
  echo "로스터에서 카메라를 찾지 못했다 — 설치 중단" >&2
  exit 1
fi
echo "로스터 카메라 ${#CAMERAS[@]}대: ${CAMERAS[*]}"

install -m 0644 "${HERE}/usb-cam@.service" "${UNIT_DIR}/usb-cam@.service"
install -m 0644 "${HERE}/usb-cam.target"   "${UNIT_DIR}/usb-cam.target"
install -m 0644 "${HERE}/dataset-collector.service" "${UNIT_DIR}/dataset-collector.service"
chmod +x "${HERE}/run_camera.sh"
systemctl daemon-reload

for cam in "${CAMERAS[@]}"; do
  systemctl enable "usb-cam@${cam}.service"
done
systemctl enable usb-cam.target
echo "부팅 자동기동 등록 완료(카메라 ${#CAMERAS[@]}대)."

# 수집기는 디스크를 계속 먹으므로 기본 미등록 — 필요할 때 수동으로 enable 한다.
echo "참고: dataset-collector.service 는 설치만 하고 enable 하지 않았다."
echo "      상시 수집이 필요하면: systemctl enable --now dataset-collector"

if [[ $START -eq 1 ]]; then
  for cam in "${CAMERAS[@]}"; do
    systemctl restart "usb-cam@${cam}.service"
  done
  sleep 3
  systemctl --no-pager --lines=0 status 'usb-cam@*' || true
fi
