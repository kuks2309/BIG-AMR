# 2026-08-24 — Tools/pc_setup 신설: Orin 개발 PC 셋업 스크립트

## 무엇을

- **신규** [Tools/pc_setup/setup_orin_dev_pc.sh](../Tools/pc_setup/setup_orin_dev_pc.sh) (127줄)
  — Jetson Orin NX(arm64, Ubuntu 22.04) 개발 PC 에 ① SSH 서버 ② Tailscale ③ VSCode 를
  설치하는 일회성 셋업 스크립트. 사용자 요청("ssh·tailscale·vscode 설정 sh 파일")으로 작성.

## 설계 결정

- **일반 사용자 실행 + 내부 sudo** — root 직접 실행은 거부(`check_platform`). `code` 등
  사용자 세션 도구가 root 소유로 초기화되는 것을 막는다. `sudo -v` 로 자격을 선확인해
  중간 프롬프트 끊김 방지.
- **재실행 안전(idempotent)** — 각 단계가 `command -v` 로 기설치를 감지해 건너뜀.
  tailscale 은 로그인 상태(`tailscale status`)까지 봐서 재접속을 강요하지 않는다.
- **Tailscale 인증 2경로** — `--authkey tskey-…` 즉시 접속 / 미지정 시 `sudo tailscale up`
  수동 URL 인증 안내만 하고 스크립트는 성공 종료(무인 설치에서 대화형 블록 방지).
- **저장소는 공식 apt 소스만** — tailscale: pkgs.tailscale.com jammy, vscode:
  packages.microsoft.com(arch=arm64 명시). `curl | sh` 원라이너 대신 keyring 을 직접 배치.
- **UFW 는 활성일 때만** OpenSSH 허용 규칙 추가 — 꺼져 있는 방화벽을 켜지 않는다.

## 검증

- `bash -n` 문법 PASS. shellcheck 는 이 PC 에 미설치라 미실행.
- `-h` 도움말 출력 확인(shebang 누출 1건 발견 → `sed -n '2,12p'` 로 수정 후 재확인 PASS).
- `--bogus` 미지의 인자 → exit 1 확인.
- **실설치 경로(apt install·tailscale up)는 미실행** — 이 PC 는 이미 3종 모두 설치돼
  있어 idempotent 건너뜀 분기만 실기 검증 가능. 신품 PC 1회 실행 검증이 남아 있다.

## 2차 (같은 날) — USB 무인 설치 킷

- **setup_orin_dev_pc.sh 확장**: `--authkey` 미지정 시 스크립트 옆 `tailscale_authkey.txt`
  의 첫 `tskey-…` 토큰을 기본값으로 채택(39-46행) — USB 에 키 파일만 두면 무인 접속.
  키 추출 로직은 더미 키 파일로 단독 검증(주석 줄 무시·토큰만 추출 확인).
- **신규** [Tools/pc_setup/make_usb.sh](../Tools/pc_setup/make_usb.sh) (110줄, root 필요)
  — USB 를 FAT32(라벨 `ORIN_SETUP`)로 포맷하고 킷 3파일(셋업 스크립트·README·
  authkey 파일)을 복사. 안전장치: 이동식(RM=1)+USB(TRAN=usb) 디스크만 허용,
  시스템 마운트 보유 장치 거부, 소거 확인 프롬프트(`--yes` 로 생략).
- **신규** [Tools/pc_setup/README_USB.txt](../Tools/pc_setup/README_USB.txt) ·
  [Tools/pc_setup/tailscale_authkey.example.txt](../Tools/pc_setup/tailscale_authkey.example.txt)
  — USB 에 실리는 안내문·키 자리표시. **실키는 저장소에 두지 않는다**(USB 에서만).
- 검증: `bash -n` PASS, `-h`·비root 거부·미지 인자 거부 실행 확인.
  **실포맷은 미실행** — 이 세션은 sudo 비밀번호가 없고 udisks 경로는 권한 정책에
  차단되어, 실행은 사용자 터미널에서 `sudo ./make_usb.sh /dev/sdX` 로 수행한다.
  현장 USB(117.2GiB, NTFS dirty 로 마운트 불가)가 첫 실사용 대상.

## 동반 기록

- 함수표 신설(이중 기록): 모듈 로컬 권위본
  [Tools/pc_setup/docs/function_table.md](../Tools/pc_setup/docs/function_table.md) +
  루트 정본(게이트 인식본) [docs/code_review/pc-setup/2026-08-24.md](../docs/code_review/pc-setup/2026-08-24.md),
  루트 집계 인덱스 [docs/sw_structure/function_table.md](../docs/sw_structure/function_table.md) 등재.
