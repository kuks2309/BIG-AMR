#!/usr/bin/env bash
# libOdoCalculator 역어셈블·레이아웃을 원본에서 받아 References/ 에 보존한다.
#
# 왜 스크립트인가 — 앞선 조사에서 산출물을 임시 디렉터리에 두었다가 세션 공백 동안
#   통째로 잃었다. 분석 결론만 문서에 남고 **근거 원자료가 사라졌다.**
#   자매 libMCLoc 은 References/seer/libMCLoc/*.asm 로 보존돼 그런 일이 없다 —
#   같은 규약을 여기에도 적용한다(보관 규약: external_reference/handling.md §1).
#
# 원본 장비가 꺼져 있으면 아무것도 만들지 않고 종료한다(빈 파일을 남기지 않는다).
set -u
cd "$(dirname "$0")/../.."
A=Tools/seer_re/amap_server.sh
D=/media/amap/6ab6980d-f090-4387-8753-a2251e75651d
SO=$D/usr/local/SeerRobotics/rbk/plugins/libOdoCalculator.so
DEST=References/seer/libOdoCalculator

# 심볼 경계 (nm -C 실측)
#   CalOdoCoef 0x14c9f0 · CalSpeed 0x14d690 · CaldPose 0x14f300 · 다음 심볼 0x14fe80
declare -A RANGES=(
  [calodocoef]="0x14c9f0 0x14d690"
  [calspeed]="0x14d690 0x14f300"
  [caldpose]="0x14f300 0x14fe80"
  [calpose_abstract]="0x15d490 0x15dc00"
)

if ! timeout 30 $A ssh "test -f $SO" 2>/dev/null; then
  echo "원본에 닿지 못했다 — amap-server 가 꺼져 있거나 하드가 안 붙었다." >&2
  echo "  tailscale status 로 상태를 확인하라." >&2
  exit 2
fi

mkdir -p "$DEST"
for name in "${!RANGES[@]}"; do
  read -r start stop <<< "${RANGES[$name]}"
  out="$DEST/$name.asm"
  echo "  $name  $start~$stop"
  timeout 300 $A ssh "objdump -d -l -C --start-address=$start --stop-address=$stop $SO" > "$out.tmp" 2>/dev/null
  # 빈 결과를 보존물로 남기지 않는다 — 그게 이번 손실의 형태였다
  if [ -s "$out.tmp" ] && grep -q "Disassembly of section" "$out.tmp"; then
    mv "$out.tmp" "$out"
  else
    rm -f "$out.tmp"; echo "    ⚠ 실패 — 보존하지 않음" >&2
  fi
done

for cls in AbstractOdometer MultiSteersOdometer MotorParam MotorVitalInfo OdometerOutput; do
  timeout 120 $A ssh "gdb -batch -q -ex 'ptype /o $cls' $SO 2>&1"
done > "$DEST/layouts.txt.tmp" 2>/dev/null
[ -s "$DEST/layouts.txt.tmp" ] && mv "$DEST/layouts.txt.tmp" "$DEST/layouts.txt" || rm -f "$DEST/layouts.txt.tmp"

echo
echo "보존물:"
ls -la "$DEST"/ 2>/dev/null | tail -n +2
echo
echo "다음: git add -f $DEST  (References/ 는 .gitignore 대상이라 -f 가 필요하다)"
