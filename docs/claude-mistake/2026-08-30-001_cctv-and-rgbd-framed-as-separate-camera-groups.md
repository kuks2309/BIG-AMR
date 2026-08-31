---
id: 2026-08-30-001
type: mistake
category: wrong-assumption
status: closed
reflected_assets:
  - /home/nvidia/.claude/projects/-home-nvidia-Project-Ford-CATL-AMR-Big-AMR/memory/biguamr-camera-port-cctv-soak.md
  - docs/claude-mistake/INDEX.md#메타-패턴
---

# 2026-08-30 16:05 (KST) — CCTV 6대와 "Orbbec RGBD 4대"를 별개 카메라군으로 오서술

## 무엇을 했는가

카메라 관리 모드 설계의 범위 질문(AskUserQuestion)에서 선택지를 "USB CCTV 6대 먼저" vs
"Orbbec 포함 전체 — **RGBD 4대까지** 한 번에"로 구성했다. 즉 CCTV 카메라군과 RGBD 카메라군이
**서로 다른 물리 카메라**이고 RGBD 는 4대라고 서술했다.

## 무엇이 잘못이었나

둘은 별개 카메라군이 아니다. **같은 물리 카메라 6대**(Orbbec Gemini E)이며, 한 대 안에서
RGB 스트림(UVC/V4L2 → `usb_cam_publisher` = CCTV 경로)과 깊이 스트림(OrbbecSDK →
`surround_depth` 경로)이 갈릴 뿐이다. "4대"는 depth 동시 구동 **실측이 4대까지**라는 문서
문구의 오전이(잘못 옮김)다. 잘못된 구도가 잘못된 범위 질문을 만들었다 — 존재하지 않는
"별개 RGBD 카메라군 포함 여부"를 사용자에게 물었다.

## 사용자 지적

> "RGBD 카메라는 6대인데무슨?"

## 원인 분석

`wrong-assumption` — 33일 묵은 메모리 요약("depth 실측은 4대까지")을 검증 없이 현재 사실로
승격했다. 반증은 이미 손안에 있었다: ① 같은 턴에 읽은 `config/camera/camera_common.yaml` 의
`by_id_prefix` 가 문자 그대로 `Orbbec_Gemini_E_RGB_Camera` (CCTV = Orbbec 카메라의 RGB 면)
② 메모리 자신도 "2026-07-28 6대 물리연결"을 적고 있었다 ③ `surround_depth.yaml` 은 CCTV 와
동일한 cam_f/cam_r/cam_lf/cam_rf/cam_rr/cam_lr 6대를 등재. 단정 전에
`orbbec_multi_bringup/config` 한 파일만 열었으면 나왔다(지적 후 수 초 만에 확인) —
「보유 원자료를 조사 후보에 넣지 않는다」 메타 패턴의 여덟 번째 변형이며, 이번 형태는
부재 단정이 아니라 **긍정 오단정**(잘못된 대수·잘못된 구도를 질문 선택지에 실어 보냄)이다.

## 재발 방지

- 메모리 `biguamr-camera-port-cctv-soak` 에 물리 정체 1줄을 추가했다: CCTV 6대 = Gemini E 의
  RGB 스트림, depth 와 같은 물리 카메라(경로만 배타). 다음 세션이 같은 오독을 하지 않도록
  요약 자체를 정정.
- INDEX §메타 패턴에 본 변형을 등재 — 교훈 확장: 「없다/미검증/위험」 단정만이 아니라
  **사용자에게 던지는 질문 선택지 속의 사실 서술**도 단정이다. 선택지에 수치·구도를 싣기 전
  그 식별자로 저장소 확인 1회.
