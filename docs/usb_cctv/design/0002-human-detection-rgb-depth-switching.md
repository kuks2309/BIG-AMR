# Design Note 0002 — 사람 감지 시 RGB→Depth 전환 운영안 (논의)

- Status: **Proposed (설계 논의 단계, 미구현)**
- Date: 2026-07-22
- Related: [ADR 0001](../adr/0001-usb-cctv-architecture.md),
  [depth 벤치마크](../performance/depth/2026-07-22_depth_640x480.md)

## 배경 / 동기

측정으로 확인된 대역 한계 (모두 단일 USB 2.0 버스):
- RGB 4대 @640x480 MJPG: **~30 fps** OK
- Depth 단독 4대 @640x480 Y11: **~14 fps** (30 미달)
- **RGB+Depth 4대 동시: 불가** (4번째 color UVC open이 LIBUSB_ERROR_BUSY로 실패)

→ 항상 RGB로 감시하다가 **사람 감지된 카메라만 depth를 확보**하면 "4대 RGB+Depth 동시"를
피하면서 필요한 순간의 depth를 얻을 수 있다.

## 실현 가능성 (드라이버 확인됨)

`orbbec_camera` 드라이버는 런타임 스트림 토글 서비스를 제공한다 (코드 확인):
- `ros_service.cpp`: `toggle_<stream>` (`std_srvs/SetBool`) → `/camX/toggle_color`, `/camX/toggle_depth`
- `toggleSensor()` 동작: `pipeline_->stop() → setupProfiles() → startStreams()`
  — 해당 카메라 파이프라인만 재시작(노드 재시작 아님). **전환 지연 = 수백 ms ~ 약 2초 공백.**

```bash
ros2 service call /cam2/toggle_depth std_srvs/srv/SetBool "{data: true}"
ros2 service call /cam2/toggle_color std_srvs/srv/SetBool "{data: false}"
```

## 변형

| | A. RGB↔Depth 완전 전환 | B. 감지 카메라 RGB+Depth 병행 |
|---|---|---|
| 감지 카메라 | depth 단독 ~30fps (RGB 잃음) | RGB~25 + depth~13fps (둘 유지) |
| 나머지 3대 | RGB@30 | RGB@30 |
| 대역 | 여유 | 빠듯 — **미검증** (단일 RGB+Depth는 실측 OK, +3 RGB MJPG는 경량) |
| 감시 유용성 | 낮음(사람 영상 손실) | 높음(사람 계속 관찰) |

권장: 감시 목적이면 **B** (단, 3xRGB + 1x(RGB+Depth) 대역 실측 선행).

## 필수 설계 요소 (결함 방지)

1. **히스테리시스/디바운스**: 경계 들락날락 → 토글 반복 → 매번 파이프라인 재시작(스래싱).
   마지막 감지 후 N초 depth 유지.
2. **동시 depth 상한**: 여러 카메라 동시 감지 시 전부 depth로 켜지면 4대 RGB+Depth(불가) 재현.
   동시 depth 카메라 수 제한(예: ≤2, 대역 실측으로 확정).
3. **감지는 RGB에서**: baseline 항상 RGB. 사람 소멸 시 depth off → RGB-only 복귀(대역 반환).
4. **전환 지연 허용성**: ~1-2초 공백이 use-case에 맞는지 확인(초단위 급하면 재검토).

## 아키텍처 (제안)

```
[4x orbbec_camera] --color--> [사람 감지기 (YOLO on RGB)]
                                     | detection(camX)
                                     v
                              [mode_manager 노드]
                     (debounce + 동시 depth cap 정책)
                                     | ros2 service /camX/toggle_depth
                                     v  RGB -> (RGB+)Depth
```

- baseline을 현재 `usb_cam_publisher`(RGB 전용 V4L2)에서 **`orbbec_camera`** 로 이전 필요
  (RGB+depth+toggle 통합 제공). VisionGuard 뷰어 토픽을 `/camX/color/image_raw`로 조정.

## 미해결 (구현 전 결정 필요)

- 감지 후 depth의 목적(사람까지 거리 / 3D 위치 / 장애물 회피)? → 변형·필요 fps 좌우.
- 동시 depth 상한 N = ? (변형 B 대역 실측 후 확정)
- 전환 지연(~1-2s) 수용 여부.

## 다음 단계 (구현 시)

1. toggle 전환 PoC: 전환 지연·fps 실측.
2. 변형 B 대역 실측: `3xRGB + 1x(RGB+Depth)` 동시 hz.
3. `mode_manager` 노드 설계/구현 (감지기는 별도).
