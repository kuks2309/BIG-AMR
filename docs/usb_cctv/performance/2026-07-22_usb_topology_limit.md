# USB 토폴로지 한계 — 카메라 대수 제약 (근본 원인 분석)

- Date: 2026-07-22
- Host: tr-orin-22 (Jetson Orin)
- **운영 결정: RGB 카메라 최대 4대 지원. 6대 연결 금지.**

## 결론 (운영 제약)

| 구성 | 상태 |
|---|---|
| RGB 4대 @640x480~1080p MJPG | ✅ 각 ~30fps 동시 (실측) |
| RGB 6대 | ❌ **금지** — 6대 중 2대만 uvcvideo 바인딩 |

## 근본 원인 (증거 기반)

6대를 한 허브에 연결한 상태에서 확인:

| 증거 | 값 |
|---|---|
| USB 컨트롤러(root) | USB 2.0 **1개**(Bus 001) + USB 3.0 1개(Bus 002) |
| Orbbec 6 RGB + 6 depth | **전부 Bus 001 (USB 2.0), 480M** — USB 3.0 허브에 꽂아도 동일 |
| RGB(UVC=USB Video Class) 영상 EP | **Isochronous**(등시성), alt 1~6, 최대 3×1024 B/마이크로프레임 |
| uvcvideo 바인딩 | 6대 중 **2대만** |

1. **RGB 영상은 isochronous** → USB 2.0에서 대역을 **예약**(주기 트래픽 ~80%, ~6000 B/마이크로프레임 상한). 6대분을 단일 버스 주기 스케줄에 못 넣음.
2. **USB 2.0 컨트롤러가 1개뿐** → 6대가 그 하나의 480M 고속 버스를 공유.
3. 카메라는 **USB 2.0 전용 고속 장치**(Gemini E datasheet: "single cable USB 2.0"; 실측 전부 480M) → SuperSpeed 경로 없음.

## 정정 (이전 오조언)

초기에 "USB 3.0 버스(Bus 002)로 분산" / "USB 3.0 허브 사용"을 권고했으나 **틀렸다**:
- 카메라가 USB 2.0 전용이라 USB 3.0 허브에 꽂아도 **USB 2.0 경로로만** 동작, 같은 컨트롤러(Bus 001)로 합류.
- **허브를 2개(3+3)로 나눠도** 같은 컨트롤러를 공유하므로 총 대역 불변. TT(Transaction Translator)는 저속 장치용이라 고속 카메라엔 무효.
- 증거: 3.0 허브 연결 후에도 6 RGB 전부 Bus 001·480M.

## 대수를 늘리려면 (근본 해법)

1. **독립 USB 호스트 컨트롤러 추가**(PCIe/M.2 USB 카드) → 대역 도메인 분리. USB2 카메라 다수의 유일한 근본책.
2. 진짜 USB 3.0(SuperSpeed) 카메라로 교체(Gemini E 불가).
3. 해상도/FPS 하향으로 등시성 예약 축소(보조책, 6대 보장 못 함).

## 관련

- [RGB 벤치마크](performance/usb_cam/) · [Depth 벤치마크](performance/depth/) ·
  [RGB→Depth 전환 운영안](../design/0002-human-detection-rgb-depth-switching.md)
