# CATL-Ford CAN-Relay

레거시 AGV(Automated Guided Vehicle) 제어 체인(ACS→PLC→Seer→모터)의 Seer↔모터 CAN(Controller Area Network) 구간에 **CAN 릴레이(Black Panda)** 를 인라인 삽입해, 자율주행 PC(Personal Computer)를 종속 주행원으로 얹는 리트로핏 프로젝트.

- 상위 아키텍처: [docs/sw_structure/system-architecture/2026-06-27.md](docs/sw_structure/system-architecture/2026-06-27.md)
- 릴레이 설계 입력(~~실측 기반~~ → **벤치 실측 + 일부 `[가설]`·실차 미검증 항목 혼재**): [docs/can_relay/](docs/can_relay/)
  - 2026-07-27 정정: 디렉터리 전체를 "실측 기반"으로 라벨할 수 없다. 각 문서가 스스로 미확증임을 표시한다 —
    `docs/can_relay/field-record-orin-nx-2026-07-25.md:5` "`[가설]`=미확증 추정(확정 금지)",
    같은 파일 `:33` "passthrough fall-back한 것으로 추정([가설])", `:40` "가짜노드 PCAN 벤치 40만회 0실패 … **실차 미검증**",
    `docs/can_relay/2026-07-07-design-inputs.md:104` "상태 = 'Switch on disabled'인데 구동됨 = 하드웨어 enable **추정**".
    **사용 전 각 문서의 `[실측]`/`[가설]` 표기를 반드시 확인할 것.**
- 구동 CAN 분석: ~~[expriments/can_data/analysis/](expriments/can_data/analysis/)~~ **(경로 없음 — 원 분석 자료 본 저장소 미보관, 위치 확인 필요)**
  - 2026-07-27 확인: `ls expriments` → No such file or directory, `find . -maxdepth 3 -name can_data` → 0건
    (`experiments/` 하위는 `capture`, `cctv_5cam_soak_20260726` 뿐). 동일한 죽은 경로를
    `docs/can_relay/2026-07-07-design-inputs.md:104` 도 근거 링크로 인용하므로, 위 "실측 기반" 주장을 뒷받침할
    원 분석 자료가 이 저장소에는 존재하지 않는다. **실제 보관 위치(타 저장소/호스트) 확인 전까지 링크를 추측으로 채우지 말 것.**

## 디렉토리 배치 규약 (2026-07-27 확정 · 2026-07-28 `Tool/` 병합 완료)

배치 기준은 **colcon 빌드 대상 여부**이고, 그 안에서 **역할(데이터 생산 ↔ 소비·표시)** 로 다시 가른다.

| 경로 | 소속 조건 | 예 |
| --- | --- | --- |
| `src/<도메인>/` | `package.xml` 을 가진 **ROS2 패키지** (colcon 이 `src/` 아래에서만 발견) | `Actuators`, `AI`, `Comm`, `Control`, `Safety`, `Sensors` |
| `src/<도메인>/…/ui/` | 그 패키지 그룹을 **표시·조작**하는 UI. 독립 `src/UI/` 도메인을 만들지 않고 **해당 패키지 아래에 종속**시킨다 | `src/Sensors/Camera/USB/ui/vision_guard` |
| `Tools/` (저장소 루트) | **비-ROS2 독립 도구**(colcon 불요, `python3` 로 즉시 실행)·펌웨어 백업·현장 킷·벤치 | `amr_test_gui`, `CameraCalibration`, `camera_service`, `Can_Relay`, `docking_field_kit`, `firmware`, `Kinematics`, `mcl2d_standalone`, `panda_bench`, `usb_cam_bench` |

- 센서 **드라이버**(데이터 발행)와 그 **UI**(구독·표시)는 같은 패키지에 섞지 않는다 — 근거: [docs/usb_cctv/adr/0001-usb-cctv-architecture.md](docs/usb_cctv/adr/0001-usb-cctv-architecture.md) '분리형 파이프라인'.
- 디렉토리를 **이동·병합·이름변경**할 때는 지목된 경로만 보지 말고 `find . -type d -iname '<이름>*'` 로 저장소를 전수 조사한 뒤 대상 목록을 먼저 합의한다 — 누락 사례: [docs/claude-mistake/2026-07-27-004](docs/claude-mistake/2026-07-27-004_repo-wide-dir-survey-skipped.md).

### 루트 도구 폴더명 — `Tools`(복수) 단일 표기

**앞으로 저장소 루트의 도구 폴더는 `Tools/` 하나뿐이다. `Tool/`(단수)·`tools/`(소문자)를 새로 만들지 않는다.**

| 항목 | 내용 |
| --- | --- |
| 정본 경로 | `Tools/` (저장소 루트, 대문자 T + 복수 s) |
| 금지 | 루트에 `Tool/`, `tools/` 신설 — 새 도구는 예외 없이 `Tools/<도구명>/` 아래 |
| 적용 범위 | **이 저장소 경로만.** 타 PC(Personal Computer)·타 저장소 경로(amap-2, `kuks2309/CAN-Relay`, 이식 원본 등)는 손대지 않는다 — 우리 규약이 미치지 않는 남의 경로다 |
| 벤더 소스도 예외 아님 | 상류(upstream) 벤더 코드가 들여온 디렉토리도 **이 저장소 안에 있으면 대상**이다. 2026-07-28 `orbbec_camera/tools/` → `Tools/` 개명(빌드 파일 6줄 동반 수정). 이 저장소는 서브모듈·상류 원격이 없어 merge 로 되돌아올 경로가 없다 — 상류 신버전을 다시 들여올 때 그 시점에 재적용하면 된다 |
| 신규 도구 절차 | ① `find . -maxdepth 1 -type d -iname 'tool*'` 로 `Tools/` 하나만 나오는지 확인 → ② `Tools/<도구명>/` 생성 → ③ 위 표 '예' 열에 이름 추가 |

**병합 이력**
- 2026-07-27 — `tools/` + `Tools/` → `Tool/`(단수)로 1차 병합. 이때 저장소 전수 조사를 건너뛰어 대상 2건을 놓쳤다([2026-07-27-004](docs/claude-mistake/2026-07-27-004_repo-wide-dir-survey-skipped.md)). 이후 같은 세션에서 정본을 `Tools/`(복수)로 재확정.
- 2026-07-28 — 잔존하던 `Tool/`(단수) 껍데기 삭제로 **병합 종결**. 삭제 시점 내용물은 타 세션 OMC 런타임 상태 5파일(`Tool/Can_Relay/panda-firmware/.omc/…`, `Tool/docking_field_kit/.omc/…`, 68 KiB)뿐이었고 소스·git 추적 파일은 0건이었다(`git ls-files Tool` → 0). 소스 실물은 이미 `Tools/` 에 있었다.
- 같은 날 루트 `.gitignore` 의 판다 펌웨어 산출물 규칙 4줄도 `Tool/…` → `Tools/…` 로 정정했다. 정정 전 그 4줄은 **매칭 0건인 죽은 규칙**이었고, `.o`/`.elf` 는 상류 저장소 자체 파일(`Tools/Can_Relay/panda-firmware/.gitignore:4,14`)이 무시하고 있었다 — 즉 유출은 없었으나 의도한 규칙이 작동하지 않는 상태였다.

**과거 문서의 `Tool/` 표기 처리** — 아래는 **역사적 사실 기술이므로 고치지 않는다**:
"구 GUI 실물은 커밋 `fdc1c51` 에 `Tool/amr_test_gui/` 경로로 남아 있다" 류의 **특정 커밋 시점 경로 인용**. 그 커밋에서는 실제로 `Tool/` 이 맞다.
고쳐야 하는 것은 **현재 저장소를 가리키는 인용**뿐이며, 해당 건은 [docs/verified_facts/2026-07-28-errata.md](docs/verified_facts/2026-07-28-errata.md) §E-2 에서 이미 정정됐다.

git 협업 모드: solo
