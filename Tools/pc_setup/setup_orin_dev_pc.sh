#!/usr/bin/env bash
# Jetson Orin NX (arm64, Ubuntu 22.04) 개발 PC 초기 설정
#   1) SSH 서버 (openssh-server) 설치·활성화
#   2) Tailscale 설치 (공식 apt 저장소) — 인증은 auth key 인자 또는 수동 URL 로그인
#   3) VSCode 설치 (Microsoft apt 저장소, arm64)
#
# 사용법:
#   ./setup_orin_dev_pc.sh                    # 전체 설치, tailscale 은 수동 인증 안내
#   ./setup_orin_dev_pc.sh --authkey tskey-…  # tailscale 을 auth key 로 즉시 접속
#   ./setup_orin_dev_pc.sh --skip-vscode      # VSCode 제외
#
# 일반 사용자로 실행한다 (필요 시점에만 내부에서 sudo). 재실행 안전(idempotent).
set -euo pipefail

AUTHKEY=""
SKIP_VSCODE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --authkey)
            AUTHKEY="${2:?--authkey 값이 없습니다}"
            shift 2
            ;;
        --skip-vscode)
            SKIP_VSCODE=1
            shift
            ;;
        -h | --help)
            sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "알 수 없는 인자: $1 (-h 참조)" >&2
            exit 1
            ;;
    esac
done

# --authkey 미지정 시 스크립트 옆 tailscale_authkey.txt 에서 키를 읽는다 (USB 무인 설치 기본).
# 파일 안의 첫 tskey-… 토큰만 취하므로 안내 주석이 섞여 있어도 된다.
if [[ -z "$AUTHKEY" ]]; then
    KEYFILE="$(cd "$(dirname "$0")" && pwd)/tailscale_authkey.txt"
    if [[ -f "$KEYFILE" ]]; then
        AUTHKEY=$(grep -m1 -oE 'tskey-[A-Za-z0-9-]+' "$KEYFILE" || true)
    fi
fi

log() { echo -e "\n=== $* ==="; }

check_platform() {
    local arch rel
    arch=$(dpkg --print-architecture)
    rel=$(. /etc/os-release && echo "${VERSION_ID}")
    if [[ "$arch" != "arm64" || "$rel" != "22.04" ]]; then
        echo "경고: 대상은 arm64/Ubuntu 22.04 인데 현재는 ${arch}/${rel} 입니다." >&2
        read -rp "계속할까요? [y/N] " ans
        [[ "$ans" =~ ^[Yy]$ ]] || exit 1
    fi
    if [[ $EUID -eq 0 ]]; then
        echo "root 로 직접 실행하지 마세요 — 일반 사용자로 실행하면 필요할 때 sudo 를 씁니다." >&2
        exit 1
    fi
    sudo -v # sudo 자격 선확인 (중간에 비밀번호 프롬프트로 끊기지 않게)
}

apt_prepare() {
    log "apt 갱신 + 공통 의존 패키지"
    sudo apt-get update
    sudo apt-get install -y curl gnupg apt-transport-https ca-certificates
}

setup_ssh() {
    log "SSH 서버"
    sudo apt-get install -y openssh-server
    sudo systemctl enable --now ssh
    # UFW 가 켜져 있을 때만 허용 규칙 추가 (꺼져 있으면 건드리지 않음)
    if command -v ufw >/dev/null && sudo ufw status | grep -q "Status: active"; then
        sudo ufw allow OpenSSH
    fi
}

setup_tailscale() {
    log "Tailscale"
    if ! command -v tailscale >/dev/null; then
        sudo mkdir -p /usr/share/keyrings
        curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/jammy.noarmor.gpg |
            sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
        curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/jammy.tailscale-keyring.list |
            sudo tee /etc/apt/sources.list.d/tailscale.list >/dev/null
        sudo apt-get update
        sudo apt-get install -y tailscale
    fi
    sudo systemctl enable --now tailscaled
    if tailscale status >/dev/null 2>&1; then
        echo "tailscale 이미 로그인됨 — 접속 단계 생략"
    elif [[ -n "$AUTHKEY" ]]; then
        sudo tailscale up --authkey "$AUTHKEY"
    else
        echo "auth key 미지정 — 아래 명령으로 브라우저 URL 인증을 진행하세요:"
        echo "  sudo tailscale up"
    fi
}

setup_vscode() {
    log "VSCode (arm64)"
    if ! command -v code >/dev/null; then
        curl -fsSL https://packages.microsoft.com/keys/microsoft.asc |
            gpg --dearmor | sudo tee /usr/share/keyrings/ms-vscode-keyring.gpg >/dev/null
        echo "deb [arch=arm64 signed-by=/usr/share/keyrings/ms-vscode-keyring.gpg]" \
            "https://packages.microsoft.com/repos/code stable main" |
            sudo tee /etc/apt/sources.list.d/vscode.list >/dev/null
        sudo apt-get update
        sudo apt-get install -y code
    fi
}

report() {
    log "설치 결과"
    echo "ssh      : $(systemctl is-active ssh) (포트 22, ip: $(hostname -I | awk '{print $1}'))"
    echo "tailscale: $(tailscale version 2>/dev/null | head -1 || echo 미설치)"
    if tailscale status >/dev/null 2>&1; then
        echo "           IP $(tailscale ip -4 2>/dev/null | head -1)"
    else
        echo "           미로그인 — 'sudo tailscale up' 필요"
    fi
    if [[ $SKIP_VSCODE -eq 0 ]]; then
        echo "vscode   : $(code --version 2>/dev/null | head -1 || echo 미설치)"
    fi
}

check_platform
apt_prepare
setup_ssh
setup_tailscale
[[ $SKIP_VSCODE -eq 0 ]] && setup_vscode
report
