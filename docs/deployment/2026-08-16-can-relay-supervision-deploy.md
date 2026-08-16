# can_relay 감시 체계 — 3개 PC 적용 가이드 (2026-08-16)

감시 체계(감시자 `relay_supervisor` · systemd 유닛 · GUI(Graphical User Interface) 감시
표시 · SIL(Software In the Loop) 하니스)를 세 장비에 적용·유지하는 절차의 정본이다.
설계 근거는 `docs/adr/2026-08-15-can-relay-node-health-supervision.md`, 검증 이력은
`docs/verified_facts/2026-08-1*-can-relay-*.md` 와 `code_updates/2026-08-15-can-relay-node-health.md`.

## 0. 공통 원칙

- **유닛은 절대 engage 하지 않는다** — 기동은 대기까지, 버스 획득은 명시 `~/engage` 또는
  감시자의 기록 기반 복귀뿐이다.
- **드라이버 유닛은 `Restart=always`** — `ros2 launch` 가 노드 사망을 exit 0 으로 삼켜
  `on-failure` 는 발동하지 않는다(실측).
- 유닛의 `ROS_DOMAIN_ID` 와 기체 YAML 은 **설치 시점 셸 환경으로 구워진다** —
  타 기체에서는 `MACHINE_YAML` 을 반드시 지정한다:
  ```
  ROS_DOMAIN_ID=<운용도메인> MACHINE_YAML=<절대경로>/<기체>.yaml \
    <저장소>/src/Comm/CAN/can_relay/install_service.sh --apply
  ```
- 판다 파이썬 라이브러리는 git 미추적 — 새 트리에는 딸려오지 않는다(§장비별 위치 참조).
- GUI 는 단일 인스턴스 잠금(`/tmp/amr_test_gui.lock`, flock)을 쓴다 — 안 뜨면
  `pgrep -f gui_node` 로 잔류 프로세스부터 확인.

## 1. 본기 — Foil_A082 젯슨 (tegra)

| 항목 | 값 |
| --- | --- |
| 실행 정본 | `~/Project/Ford-CATL-AMR/Big-AMR-deploy` (main 고정 detached worktree) |
| 운용 도메인 | **125** (사용자 셸 export — CLI 조작 시 명시 필요) |
| 판다 라이브러리 | 본 저장소 워크트리 사본에 심볼릭 링크(이미 구성됨) |

**main 갱신 반영 절차** (전부 이 순서대로):
```
cd ~/Project/Ford-CATL-AMR/Big-AMR-deploy
git fetch && git checkout --detach origin/main
colcon build --packages-select trnav_msgs can_relay --symlink-install
src/Comm/CAN/can_relay/install_service.sh --apply     # sudo 비밀번호 필요
```
`enable --now` 는 기동 중 유닛을 재시작하지 않는다 — 코드 교체 후에는
`systemctl restart amr-can-relay amr-can-relay-supervisor` 로 재기동을 확인한다.

## 2. lgit-c6-4 — 같은 Foil_A082 의 협동로봇 팔 PC (QD 주행계)

| 항목 | 값 |
| --- | --- |
| 접속 | `ssh tc@lgit-c6-4` (tailscale IP, 일반 sshd — 키 등록 필요) |
| 워크스페이스 | `~/LGIT_C6_MoMa` (`src/Comm/CAN/can_relay`, **git 아님** — rsync 사본) |
| 운용 도메인 | **44** (`~/.bashrc` export) |
| 기체 YAML | `config/machine/lgit_moma_qd.yaml` (조향 48,332.8 counts/° — **Foil 57,344 와 절대 혼용 금지**) |
| 판다 라이브러리 | 패키지 동봉 `src/Comm/CAN/can_relay/vendor/panda` → `~/LGIT_C6_MoMa/Tools/docking_field_kit/panda` 심볼릭 링크(구성됨 — `link.py` 탐색 경로) |

### 2-1. 포크 경계 — 덮어쓰면 안 되는 파일

이 트리는 기체 적응 **포크**다. 정본(Big-AMR)에서 갱신을 밀 때 다음은 **제외**한다:

| 포크 유지(덮어쓰기 금지) | 이유 |
| --- | --- |
| `config/` 전체 | 기체 캘리브레이션·기체 전용 배포값 |
| `can_relay/ui/app.py` | QD 실측 JOG(조그 표)·Seer 조그·기체 UI (감시 표시는 2026-08-16 이식됨) |
| `can_relay/ui/backend_direct.py` | 기체 선택형(`CAN_RELAY_MACHINE`) 직결 백엔드 — 정본보다 진화 |
| `test/test_seer_jog.py`·`test_gui_node.py`·`test_link.py`·`test_wheel_view.py`·`test_steer_zero_return.py` 및 포크 전용 시험들 | 포크 UI·실측 앵커에 결합 |
| `test/conftest.py` 의 LGIT 헬퍼 절 | 포크 시험이 쓴다(정본 conftest 에도 동봉됨 — 통째 덮어쓰기는 가능) |

**정본에서 미는 것(코어)**: `can_relay/{backend,driver_node,link,protocol,safety,health,supervisor,home_and_zero}.py` ·
`ui/{backend_base,backend_ros2,gui_node}.py` · `launch/` · `systemd/` · `install_service.sh` ·
`setup.py` · 코어 시험들 · `Tools/can_relay_sil` · `Tools/can_relay_field`.

### 2-2. 갱신·검증 절차

```
# (본기에서) 코어만 rsync — 제외 목록 준수
rsync -av --exclude='__pycache__' --exclude='config/' \
      --exclude='can_relay/ui/backend_direct.py' --exclude='can_relay/ui/app.py' \
      --exclude='vendor/' --exclude='test/test_seer_jog.py' \
      --exclude='test/test_gui_node.py' --exclude='test/test_link.py' \
      --exclude='test/test_wheel_view.py' --exclude='test/test_steer_zero_return.py' \
      <정본>/src/Comm/CAN/can_relay/  tc@lgit-c6-4:LGIT_C6_MoMa/src/Comm/CAN/can_relay/

# (lgit 에서) 빌드 — 구 산출물과 symlink 충돌 시 build/install 의 can_relay 만 삭제 후 재빌드
cd ~/LGIT_C6_MoMa && source /opt/ros/humble/setup.bash
colcon build --packages-select can_relay --symlink-install && source install/setup.bash

# 검증 — pytest 9 라 ROS 플러그인 자동로드를 끈다. 라이브 도메인 간섭을 피해 빈 도메인 사용
export QT_QPA_PLATFORM=offscreen ROS_DOMAIN_ID=77 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python3 -m pytest src/Comm/CAN/can_relay/test -q \
  --ignore=src/Comm/CAN/can_relay/test/test_backend_swap.py \
  --ignore=src/Comm/CAN/can_relay/test/test_port_equivalence.py \
  --ignore=src/Comm/CAN/can_relay/test/test_steer_zero_return.py \
  --ignore=src/Comm/CAN/can_relay/test/test_gui_node.py
python3 Tools/can_relay_sil/sil_health.py        # 감시 체계 종단 검증(모의 링크)
```
제외 사유: `backend_swap`·`port_equivalence` 는 본기에만 있는 `Tools/amr_test_gui` 원본
대조 시험 · `steer_zero_return` 은 §2-4 의 의미론 변화로 무효 · `gui_node` 는 라이브
도메인·Qt 조합에서 원격 실행이 불안정(잔여 항목).

### 2-3. 감시 유닛 설치 (sudo — 사람 실행)

```
ROS_DOMAIN_ID=44 MACHINE_YAML=$HOME/LGIT_C6_MoMa/src/Comm/CAN/can_relay/config/machine/lgit_moma_qd.yaml \
  ~/LGIT_C6_MoMa/src/Comm/CAN/can_relay/install_service.sh --apply
```
설치 출력의 「저장소」가 `~/LGIT_C6_MoMa` 인지, `systemctl cat amr-can-relay` 의
ExecStart 에 `machine_file:=…lgit_moma_qd.yaml` 이 박혔는지 확인한다.

### 2-4. ⚠ 알려진 의미론 변화 — QD 실기 확인 전 운용 금지 항목

포크의 구판 backend 는 **호밍 안에 조향 0° 복귀를 내장**했었다(`zero_return_enabled` 류).
정본 코어는 그것을 **펌웨어 GOZERO + `home_and_zero` CLI(Command Line Interface)** 로
분리했다. 이번 이식으로 lgit 의 `~/home` 은 더 이상 자체 0° 복귀를 하지 않는다 —
**QD 기체에서 호밍 후 자세가 어디서 멎는지 실기 확인 전까지, lgit 호밍은 감시자
자동 복귀 경로에서만 쓰고 수동 호밍 후에는 `home_and_zero` 를 쓸 것**
(`ros2 run can_relay home_and_zero --ros-args -p confirm:=true -p target_node:=can_relay_node`).
포크 시험 `test_steer_zero_return.py` 는 이 확인이 끝날 때까지 판정 보류로 남긴다.

## 3. amap-server — LGIT 정본 저장소 보관처

| 항목 | 값 |
| --- | --- |
| 접속 | `Tools/seer_re/amap_server.sh` 경유(계정 `amap`, 첫 접속 60 s+) |
| 정본 저장소 | `/home/amap/T-Robotics/LGIT-C6-Cobot /LGIT-C6-MOMA` (⚠ 디렉터리명 **후행 공백**) |

lgit 워크스페이스는 git 이 아니므로, lgit 에 반영한 상태를 **이 저장소에 커밋해야
이력이 남는다.** 반영 경로(본기 경유):
```
ssh tc@lgit-c6-4 'tar -C ~/LGIT_C6_MoMa/src/Comm/CAN --exclude=__pycache__ -cf - can_relay' > /tmp/can_relay.tar
scp /tmp/can_relay.tar amap@amap-server:/tmp/
ssh amap@amap-server 'cd "/home/amap/T-Robotics/LGIT-C6-Cobot /LGIT-C6-MOMA/src/Comm/CAN" && tar -xf /tmp/can_relay.tar && cd .. && git add Comm/CAN/can_relay && git commit'
```
push 는 그 장비의 GitHub 자격증명 유무에 따른다(`github.com/kuks2309/LGIT-C6-Cobot`).

## 4. 남은 것 (이 가이드 작성 시점)

- lgit 감시 유닛 설치(§2-3)는 sudo 라 미실행 — 사람 몫.
- lgit `test_gui_node` 원격 실행 불안정 — 화면 있는 자리에서 확인.
- §2-4 의 QD 호밍 후 자세 실기 확인.
- 포크 통합(backend_direct 의 기체 선택 방식을 정본에 역이식해 포크 경계를 줄이는 것)은
  부채 registry 의 해당 항목을 따른다.
