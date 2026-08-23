#!/usr/bin/env bash
# amr-telegram-notifier.service 설치/상태/제거. 인자 없이 실행하면 dry-run 만 한다.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
UNIT_NAME="amr-telegram-notifier.service"
UNIT_SRC="$HERE/systemd/$UNIT_NAME"
UNIT_DST="/etc/systemd/system/$UNIT_NAME"
CONFIG="$REPO/config/telegram_notifier/telegram.json"
EXAMPLE="$REPO/config/telegram_notifier/telegram.example.json"

render() {
    sed -e "s|__PKGROOT__|$HERE|g" -e "s|__CONFIG__|$CONFIG|g" "$UNIT_SRC"
}

case "${1:---dry-run}" in
    --apply)
        if [ ! -f "$CONFIG" ]; then
            echo "설정이 없다: $CONFIG" >&2
            echo "  cp \"$EXAMPLE\" \"$CONFIG\" && chmod 600 \"$CONFIG\" 후 token·chat_id 를 채워라" >&2
            exit 1
        fi
        render | sudo tee "$UNIT_DST" >/dev/null
        sudo systemctl daemon-reload
        sudo systemctl enable --now "$UNIT_NAME"
        systemctl status --no-pager "$UNIT_NAME" || true
        ;;
    --status)
        systemctl status --no-pager "$UNIT_NAME" || true
        ;;
    --remove)
        sudo systemctl disable --now "$UNIT_NAME" 2>/dev/null || true
        sudo rm -f "$UNIT_DST"
        sudo systemctl daemon-reload
        echo "제거 완료 (설정 파일은 보존: $CONFIG)"
        ;;
    *)
        echo "# dry-run — --apply 시 $UNIT_DST 에 설치될 내용:"
        render
        echo
        echo "# 적용: $0 --apply | 상태: $0 --status | 제거: $0 --remove"
        ;;
esac
