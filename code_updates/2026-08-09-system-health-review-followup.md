# 2026-08-09 — `src/Safety/system_health` 코드 리뷰 권고 반영

> 수정 이력의 기록처. 주석은 현재 코드의 사실만 담고 이력은 여기와 커밋 메시지가 담는다
> (`docs/claude_guideline/coding/conventions.md:26`, `hooks/coding-comment-gate.py`).

- 사용자 지시: 2026-08-09 "권고안대로 수정해주세요"
- 사전승인: `docs/adr/2026-08-09-system-health-review-followup.md` (Status: Proposed)
- 근거 리뷰: `docs/code_review/system_health/2026-08-07.md` (REQUEST CHANGES — High 1 · Medium 5 · Low 9)
- 조치 후 인벤토리: `docs/code_review/system_health/2026-08-09.md`
- 회귀: `python3 -m pytest test -q` → **183 passed → 220 passed** (신규 37건)

## 1차 — 주석 정정 21건 (로직 변경 0줄)

ADR 원문 대조로 소스 주석의 ADR 인용을 고쳤다. 상세 대조표는
`docs/code_review/system_health/2026-08-07.md` §부록 A.

| 유형 | 건수 | 요지 |
| --- | --- | --- |
| 오귀속 | 2 | `sysfs.py` 이유 ②는 §Decision 3 이 아니라 §Decision 9 소관 · `thresholds.py` 후속과제 1 은 온도만 대상 |
| ADR 미지정 | 10 | 한 파일에 두 ADR 이 섞인 채 `§Decision N` 만 적혀 있어 `sampler.py` 의 `§Decision 3`·`4` 가 서로 다른 ADR 을 가리켰다 |
| 근거 누락 | 1 | `_stop_requested` 주석에 ADR 2026-07-28 §Decision 8 추가 |
| 주석 규율 | 2 | 1차 수정이 넣은 "…이 아니라 …다" 식 정정 경위를 걷어내고 사실만 남김 |
| S6 게이트 | 6 | 절대형 부정 옆에 확인 명령·문서 앵커 부재 — 뜻을 명확히 하거나 근거를 문장 옆에 붙임 |

## 2차 — 리뷰 권고 반영 (High 1 · Medium 5 · Low 9)

| 파일 | md5(전 → 후) | 변경 |
| --- | --- | --- |
| `system_health/thresholds.py` | `2da7d7ac` → `a65d64b0` | 설정 값 타입·WARN/ERROR 순서 검증(`_coerce`·`THRESHOLD_PAIRS`), 지역명 `rate` 분리 |
| `system_health/sampler.py` | `bc5f7b0d` → `8f0a7d4c` | 인자 범위 검증, 절대 시각 스케줄, 설정 오류를 기동 시 `SystemExit` |
| `system_health/report.py` | `557ca9d0` → `4edb8485` | 0-주기 방어, `--since` 성장률 구간 일치, `records`/`files`/`max_samples` 주입, 완독 1회 |
| `system_health/webview.py` | `156cf164` → `ed5a2006` | `esc()` 이스케이프, `LEVEL_VIEW` 페이지 주입, `/api/report` 표본 상한 |
| `system_health/sysfs.py` | `bc9ae8ef` → `f82718ae` | `CpuSnapshot.core_ids` 로 코어 번호 join, 미사용 상수 2개 삭제 |
| `system_health/ringlog.py` | `0fa272fa` → `e6ecc711` | `enforce_limits` 총량 1회 계산 + 삭제분 차감 |
| `system_health/cliargs.py` | (신규) `59b7d428` | 인자 범위 검증 공용 모듈 |
| `setup.py` | `29a54b9d` → `308c68fb` | 유닛 `glob` |
| `install_service.sh` | `c9462401` → `088f12a5` | `REPO` 를 스크립트 위치에서 유도, 유닛 템플릿 치환 |
| `systemd/*.service` | `5efae91b`·`37bd1752` → `97410466`·`600c3656` | `@REPO@`·`@USER@`·`@GROUP@` 자리표시자 |

패키지 전체 sha256: `2d4a9af1…` → `86477744cb5bc2fe4d0985134be7e7c5a46cdf0ca6c36f1fda0a783b7443225b`

### 실측 확인

```
pytest test -q                     183 passed → 220 passed
--interval 0                       error: 0 보다 커야 한다 (exit 2)   [전: 3초에 표본 757개]
주기 드리프트 (--interval 1)        평균 1.0000 s                      [전: 1.0073 s]
install_service.sh (이 PC)          /home/amap/... 로 유도             [전: /home/nvidia/... 고정]
systemd-analyze verify (렌더본)     exit 0
checks/index-fresh.sh              ✓ 최신 (284 심볼로 재생성)
checks/dup-signature.sh            ✓ 중복 0
checks/banned-pattern.sh           ✓ 금지 패턴 0
checks/format.sh                   ✓ 준수
checks/adr-fields.sh               ✓ 본 ADR 위반 0
review-claim-lint.py (소스·문서)    ✓ FAIL 0
```

### 되돌림

ADR §Rollback 참조 — 위 "전" md5 로 복원하고, 설치된 유닛은 `./install_service.sh --remove both`
후 복원본으로 재설치한다. 로그·임계값 파일은 보존된다.

### 남은 것

**외부 lane 검증 대기** — 저자는 조치의 적정성에 `APPROVE` 를 찍을 수 없다
(`review.md` 룰 11 · `coding.md` §5). ADR 은 그 검증 후 Accepted 로 올린다.

---

## 3차 (2026-08-10) — LGIT MOMA 이식에서 나온 플랫폼 적응 변경 역동기화

LGIT MOMA 이식 과정에서 x86_64 실기(lgit-c6-4)에 맞춰 고친 것을 **상류로 되돌렸다**. 두 저장소의
`system_health` 트리를 하나로 유지하기 위함이다(LGIT `ADR-002` §Decision 1·2).

| 파일 | md5(전 → 후) | 변경 |
| --- | --- | --- |
| `system_health/sysfs.py` | `f82718ae` → `4d10900f` | `read_fan` 이 Tegra `pwm-fan` 다음 범용 hwmon(`fan1_input`/`pwm1`)을 탐색 · `read_gpu` 가 devfreq 다음 i915(`gt_*_freq_mhz`, MHz→Hz)를 탐색 · 전역 `_DRM_ROOT`·`_HZ_PER_MHZ` 추가 |
| `install_service.sh` | `088f12a5` → `50027d08` | `config/system_health/service.env` 를 있으면 source · `HEALTH_PORT`(기본 8770) · `render_unit` 에 `@PORT@` 치환 · `warn_if_port_taken()` 신규 |
| `systemd/amr-health-webview.service` | `600c3656` → `05e1504a` | `--port 8770` → `--port @PORT@`, 템플릿·포트 주석 |

**Tegra 동작은 바뀌지 않는다** — 두 리더 모두 기존 경로를 먼저 보고, 못 찾을 때만 새 경로를 본다.

### 실측 확인

```
pytest test -q (본 저장소)          220 passed
checks/index-fresh.sh              ✓ 최신
checks/dup-signature.sh            ✓ 중복 0
checks/banned-pattern.sh           ✓ 금지 패턴 0
checks/format.sh                   ✓ 준수
review-claim-lint (sysfs.py·문서)   ✓ FAIL 0
함수표 앵커 108행 대조              일치 108 / 불일치 0 (정본·병기본 양쪽)
LGIT ↔ 상류 ↔ LGIT 실기 md5        3자 동일 (sysfs.py 4d10900f · install_service.sh 50027d08 · webview.service 05e1504a)
```

### 미실행 — 원본 장비(Orin)

**Orin 에는 배포하지 않았다.** 그 장비에서 `amr-health-sampler`·`amr-health-webview` 가 active 로
돌고 있어 배포는 별도 결정이다. 따라서 본 변경의 **Jetson 실기 재검증은 하지 않았다** — 회귀
테스트와 "기존 경로 우선" 구조로만 무해함을 주장한다.

배포하기로 하면 유닛 재설치가 필요하다(`--port @PORT@` 자리표시자 때문). 그 장비의 포트 8770 은
system_health 자신이 쓰고 있으므로 `service.env` 없이 기본값으로 그대로 동작한다.
