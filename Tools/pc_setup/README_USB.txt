ORIN_SETUP USB — Jetson Orin NX (Ubuntu 22.04) 개발 PC 셋업 킷
================================================================

새 PC 에서:

  1. 이 USB 를 꽂고 터미널을 연다
  2. 실행:
       bash /media/$USER/ORIN_SETUP/setup_orin_dev_pc.sh
  3. 끝. SSH 서버·Tailscale·VSCode 가 설치된다.

tailscale 무인 접속:
  - tailscale_authkey.txt 에 실제 auth key(tskey-…)가 들어 있으면
    로그인 절차 없이 자동으로 tailnet 에 붙는다.
  - 자리표시 상태(키 없음)면 설치 후 `sudo tailscale up` 으로
    브라우저 URL 인증을 한 번 하면 된다.
  - auth key 발급: https://login.tailscale.com/admin/settings/keys
    (Reusable + 만료기간 설정을 권장. 키는 자격증명이므로 USB 분실 시 폐기할 것)

선택 인자:
  --skip-vscode   VSCode 설치 생략
  --authkey …     키 파일 대신 직접 지정
