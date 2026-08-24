#!/usr/bin/env bash
# USB 배포 킷 제작 — USB 를 FAT32(라벨 ORIN_SETUP)로 포맷하고 셋업 킷을 복사한다.
# 킷 구성: setup_orin_dev_pc.sh + tailscale_authkey.txt + README.txt
#
# 사용법 (root 필요):
#   sudo ./make_usb.sh /dev/sdX                     # 포맷 + 복사, authkey 는 자리표시
#   sudo ./make_usb.sh /dev/sdX --authkey tskey-…   # 무인 tailscale 접속 키까지 심기
#   sudo ./make_usb.sh /dev/sdX --yes               # 확인 프롬프트 생략
#
# 안전장치: 대상은 이동식(RM=1)·USB(TRAN=usb) 디스크만 허용. 그 외 장치는 거부.
set -euo pipefail

DEV=""
AUTHKEY=""
ASSUME_YES=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --authkey)
            AUTHKEY="${2:?--authkey 값이 없습니다}"
            shift 2
            ;;
        --yes)
            ASSUME_YES=1
            shift
            ;;
        -h | --help)
            sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        /dev/*)
            DEV="$1"
            shift
            ;;
        *)
            echo "알 수 없는 인자: $1 (-h 참조)" >&2
            exit 1
            ;;
    esac
done

require_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "root 필요: sudo $0 ${DEV:-/dev/sdX} …" >&2
        exit 1
    fi
}

validate_device() {
    [[ -n "$DEV" ]] || { echo "대상 장치를 지정하세요 (예: /dev/sda)" >&2; exit 1; }
    [[ -b "$DEV" ]] || { echo "블록 장치가 아닙니다: $DEV" >&2; exit 1; }
    local rm tran
    rm=$(lsblk -dn -o RM "$DEV" | tr -d ' ')
    tran=$(lsblk -dn -o TRAN "$DEV" | tr -d ' ')
    if [[ "$rm" != "1" || "$tran" != "usb" ]]; then
        echo "거부: $DEV 는 이동식 USB 디스크가 아닙니다 (RM=$rm TRAN=$tran)" >&2
        exit 1
    fi
    if lsblk -no MOUNTPOINT "$DEV" | grep -q '^/$\|^/boot'; then
        echo "거부: $DEV 에 시스템 마운트가 있습니다" >&2
        exit 1
    fi
}

confirm() {
    echo "포맷 대상: $DEV — $(lsblk -dn -o SIZE,MODEL "$DEV")"
    echo "이 장치의 모든 데이터가 지워집니다."
    if [[ $ASSUME_YES -eq 0 ]]; then
        read -rp "계속할까요? [y/N] " ans
        [[ "$ans" =~ ^[Yy]$ ]] || exit 1
    fi
}

do_format() {
    # 남은 마운트를 전부 해제한 뒤 msdos 테이블 + 단일 FAT32 파티션으로 만든다
    local p
    for p in $(lsblk -no MOUNTPOINT "$DEV" | grep '^/' || true); do
        umount "$p"
    done
    wipefs -a "$DEV"
    parted -s "$DEV" mklabel msdos mkpart primary fat32 1MiB 100%
    partprobe "$DEV" && sleep 1
    PART="${DEV}1"
    [[ -b "$PART" ]] || { echo "파티션 생성 실패: $PART" >&2; exit 1; }
    mkfs.vfat -F 32 -n ORIN_SETUP "$PART"
}

do_copy() {
    local src mnt
    src="$(cd "$(dirname "$0")" && pwd)"
    mnt=$(mktemp -d)
    mount "$PART" "$mnt"
    cp "$src/setup_orin_dev_pc.sh" "$mnt/"
    cp "$src/README_USB.txt" "$mnt/README.txt"
    if [[ -n "$AUTHKEY" ]]; then
        printf '%s\n' "$AUTHKEY" > "$mnt/tailscale_authkey.txt"
    else
        cp "$src/tailscale_authkey.example.txt" "$mnt/tailscale_authkey.txt"
    fi
    sync
    ls -l "$mnt"
    umount "$mnt" && rmdir "$mnt"
}

require_root
validate_device
confirm
do_format
do_copy
echo "완료: $DEV 이(가) ORIN_SETUP 킷으로 준비됐습니다. 빼서 새 PC 에 꽂으세요."
