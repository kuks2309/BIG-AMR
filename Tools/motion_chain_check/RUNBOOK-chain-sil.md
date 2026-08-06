# 모션→모터 전 체인 SIL 런북

`motion_chain_sil.launch.py` 로 **액션 → mux → translator → can_relay** 를 한 번에 띄우고
`/motor/low_cmd` 의 raw counts 까지 확인하는 절차. 기존 `sil_*.launch.py` 는 플랜트가
`/motor/wheel_cmd` 를 직접 받아 translator·can_relay 를 건너뛰었다 — 본 런치가 그 구간을 넣는다.

## 0. 안전 — 이 절차는 차량을 움직이지 않는다

| 게이트 | 근거 |
| --- | --- |
| `link:=mock` (기본) → 하드웨어 **무접속** | `driver_node.py:167-169` |
| 기동만으로 제어권을 잡지 않음 | `driver_node.py:231` |
| 제어권 없으면 백엔드 기동 거부 | `backend.py:170-171` |
| 호밍 전 조향 지령 거부 | `backend.py:270,307` `require_homed_for_steer` |

⚠ **실행 전 반드시 확인** — 같은 ROS 도메인에 **다른 can_relay 인스턴스가 없어야 한다.**
있으면 `/motor/low_cmd` 를 그쪽도 구독하므로, 그 인스턴스가 실 하드웨어에 제어권을 쥐고
있으면 **실차가 움직인다.**

```bash
ps -eo pid,etime,cmd | grep [c]an_relay        # 잔류 프로세스
ros2 node list | grep can_relay                # 같은 도메인의 노드
lsusb | grep -i comma                          # 판다 연결 여부
```

**도메인 격리를 기본으로 쓴다** — 아래 모든 명령을 같은 셸에서:

```bash
export ROS_DOMAIN_ID=42
```

## 1. 기동

```bash
cd <워크스페이스>
source /opt/ros/humble/setup.bash && source install/setup.bash
export ROS_DOMAIN_ID=42

ros2 launch trnav_motion_mux motion_chain_sil.launch.py action:=turn source_id:=5
#   action: crab_linear(4) | spin(3) | turn(5)   ← source_id 를 함께 맞출 것
#   link:   mock(기본) | panda
#   plant:  true(기본) | false
```

정상 기동 확인 — 노드 8개와 can_relay 의 세 줄:

```
기체 'Foil_A082' · 호밍 firmware (활성=True) · 조향 한계 체인 ±115.0° / 벤치 ±90.0°
링크 = mock (하드웨어 무접속)
can_relay 대기 — 제어권 미획득. `~/engage true` 로 획득하세요
```

## 2. 관측 대상

| 토픽 | 무엇을 보는가 |
| --- | --- |
| `/motion/wheel_cmd/<action>` | 액션이 낸 SI 지령(m/s, rad). 조향이 90° 를 넘는가(크랩) |
| `/motor/wheel_cmd` | mux 통과 여부 — 안 나오면 active source 가 틀린 것 |
| `/motor/low_cmd` | **translator 가 만든 raw counts** — 스케일·부호가 여기서 확정된다 |
| `/motor/low_state` | can_relay 피드백(조향은 **홈 기준 상대** counts) |
| `/diagnostics` | can_relay 의 제어권·거부 건수·노드별 pos/sw |

도구:

```bash
python3 Tools/motion_chain_check/sil_record_steer.py --topic /motion/wheel_cmd/turn --seconds 60
python3 Tools/motion_chain_check/measure_crab_yaw_authority.py 40     # 크랩 전용
python3 Tools/motion_chain_check/check_chain_contract.py              # 정적 계약 대조
```

## 3. 기대값 (Foil_A082)

```
조향  1° = 57,344 counts        (translator: 65536 × 315 / 360)
구동  1 mm/s = 24.447 units     (60 × 32 × 10 / (2π × 0.125) / 1000)
조향 원점  node3 7,871,815c · node4 7,840,086c   ← can_relay 가 더한다(상류는 홈 기준 상대)
클램프  체인 ±115° · 벤치 ±90°
```

`/motor/low_cmd` 의 `target_pos` 는 **홈 기준 상대**다 — 0 이면 직진이다. 절대 counts(7.8M)가
보이면 상류가 원점을 잘못 더한 것이다.

## 4. can_relay 를 실제로 동작시키려면 (mock 에서도 필요)

```bash
ros2 service call /can_relay_node/engage std_srvs/srv/SetBool "{data: true}"
ros2 service call /can_relay_node/home   std_srvs/srv/Trigger {}     # ⚠ 실 링크면 물리 스윙 100°+
```

engage 전에는 백엔드가 기동하지 않아 지령이 CAN 으로 나가지 않는다(mock 이면 MockLink 로).
호밍 전에는 조향 지령이 거부된다 — 진단의 `rejected_commands` 가 오른다.

## 5. 종료

```bash
# Ctrl-C 로 런치 종료 (can_relay 정상 종료 경로: 정지 송신 후 하강)
ps -eo pid,cmd | grep [c]an_relay      # 잔류 확인 — 남아 있으면 kill -INT
```

⚠ 런치를 백그라운드로 돌렸다면 **끝난 뒤 반드시 잔류 프로세스를 확인**한다.
2026-08-05 에 세션 종료 후에도 `can_relay_node` 가 14시간 살아남아 판다를 점유한 사례가 있다.
