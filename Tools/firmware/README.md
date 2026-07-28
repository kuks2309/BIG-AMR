# 펌웨어 소스 백업 (git bundle)

- 원본: amap-1 `amap@100.116.195.65:~/T-Robotics/CAN_Relay/panda` (브랜치 can-relay-docking, HEAD 08c23b53)
- 번들: `panda-canrelay.bundle` (git bundle --all, 전체 이력·브랜치 완전 보존, md5 8ea779dc5dd32e5d00cd29012df4bb99)
- 복원: `git clone panda-canrelay.bundle panda && cd panda && git checkout can-relay-docking`
- 이중화 위치: amap-1(원본) · 이 저장소 `Tools/firmware/` · orin-nx Big-AMR/`Tools/Can_Relay/`(번들+작업트리 panda-firmware/)
- 빌드 산출물 panda.bin.signed 는 git 미추적 — 배포본은 `Tools/docking_field_kit/panda.bin.signed`
