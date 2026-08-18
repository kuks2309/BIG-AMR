# can_relay — 심박 억제 단독 관측 실기 실험 (2026-08-16)

## 목적

억제 경로(**제어 스레드 생존 + ROS 계층 정체** → 의도적 심박 중단 → 펌웨어에 정지 위임)를
실기에서 단독으로 밟는다. 전 스레드 동결(SIGSTOP)로는 제어 스레드도 함께 죽어 이 경로를
검증할 수 없었다(`2026-08-16-can-relay-zombie-freeze-field.md` §관측의 한정).

## 조건

| 항목 | 값 |
| --- | --- |
| 일시 | 2026-08-16 10:27~10:29 (KST) |
| 기체 | Foil_A082 (판다 실링크) |
| 코드 | `main` `bbf0f71` — **제품 코드 무변경** |
| 파라미터 | 기본값 — `ros_alive_timeout_s` 2.0 s · 진단 1 Hz · 두절 3.0 s · 재생성 15 s |
| 안전 | 구동·조향 지령 없음, 실제 축 움직임 0 |

## 주입 방법 (재현 절차)

진단 타이머(`_on_diag_timer` — `mark_ros_alive` 호출원)는 **기본 콜백 그룹**
(MutuallyExclusive)에 있다. 같은 그룹에 콜백 하나를 더 달아 잠재우면 다중 스레드
실행기라도 진단 타이머가 그동안 돌지 못하고, 제어 스레드(파이썬 스레드, 실행기 무관)는
계속 돈다 — 정확히 억제 경로의 전제다.

제품 코드를 바꾸지 않기 위해 `sitecustomize` 주입을 썼다: `PYTHONPATH` 앞에 둔
디렉터리의 `sitecustomize.py` 가 `CAN_RELAY_TEST_STALL=1` 일 때만
`CanRelayNode.__init__` 뒤에 `~/test_stall`(Float64, 기본 그룹) 구독을 덧붙이고,
콜백은 받은 초만큼 `time.sleep` 한다.

```python
# sitecustomize.py 핵심부 (전체는 이 절차로 재작성 가능)
if os.environ.get("CAN_RELAY_TEST_STALL") == "1":
    from can_relay import driver_node as _dn
    _orig = _dn.CanRelayNode.__init__
    def _patched(self, *a, **kw):
        _orig(self, *a, **kw)
        from std_msgs.msg import Float64
        def _stall(msg):
            time.sleep(float(msg.data))     # 기본 그룹 점유 = 진단 타이머 정지
        self._test_stall_sub = self.create_subscription(
            Float64, "~/test_stall", _stall, 1)   # callback_group 미지정 = 기본 그룹
    _dn.CanRelayNode.__init__ = _patched
```

실행: engage(RUNNING) 후 `ros2 topic pub --once /can_relay_node/test_stall
std_msgs/msg/Float64 "{data: 10.0}"`.

## 관측 (로그 시각, 에포크 초 하위부)

| 시각 | 사건 |
| --- | --- |
| …508.0 | 정체 시작(10 s) — 기본 그룹 콜백 점유 |
| …509.9 | **「⚠ ROS 계층 정체 2.1s (임계 2.0s) — 심박 중단. 펌웨어 fail-safe 에 정지를 넘긴다」** — 제어 스레드가 직접 억제를 걸었다(실행기 정지 중에 나온 로그라는 것 자체가 제어 스레드 생존 증거) |
| …511.0 | 감시자 `RUNNING → WAIT — 진단 두절 3.2s · 프로세스는 있다` |
| …518.0 | 정체 해제(주입 콜백 반환) |
| …518.5 | 감시자 `WAIT → RUNNING` — 10 s 정체는 DDS 세션을 깨지 않았고 참여자 재생성(15 s)도 발동 전(설계 여유 확인) |
| 직후 | 진단 `engaged=True · hb_suppressed=False · 전 축 fresh=True · bus 오류 0` — 억제는 ROS 생존 표시가 새로워지자 자동 해제 |

## 판정

| 주장 | 판정 |
| --- | --- |
| ROS 정체 + 제어 스레드 생존 시 심박 억제 발동 (임계 2.0 s) | **실기 PASS** (2.1 s 발동) |
| 정체 해소 시 억제 자동 해제·정상 복귀 | **실기 PASS** |
| 감시자는 같은 구간을 두절(WAIT)로만 보고 개입하지 않음 | **실기 관측** (설계 일치 — 정지는 펌웨어 소관) |

## 관측의 한정

- 억제된 ~8 s 동안 **펌웨어가 실제로 fail-safe(구동 0 ×3·릴레이 개방)를 수행했는지**는
  버스 캡처 없이 판정 불가 — 이전 실험들과 동일한 한정. 정체 해제 후 폴링 피드백이
  정상(`fresh=True`)인 것은 판다 경유 경로가 살아 있음을 시사할 뿐이다.
- 10 s 단일 정체만 시험했다 — 억제↔재개를 여러 번 반복하는 시나리오는 미시험.
- 주입은 시험 세션의 환경 변수로만 활성화된다 — 배포 실행에는 존재하지 않는다.
