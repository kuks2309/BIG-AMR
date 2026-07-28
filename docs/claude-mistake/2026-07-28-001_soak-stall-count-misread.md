---
id: 2026-07-28-001
type: rule-violation
category: verify-skip
status: closed
reflected_assets:
  - Tools/usb_cam_bench/soak_stats.py:19-24
  - Tools/usb_cam_bench/soak_stats.py:96-104
  - Tools/usb_cam_bench/test_soak_stats.py (test_summarize_display_equal_deltas_are_not_stalls)
---

# 2026-07-28 08:25 (KST) — 내구 로그의 "정지 구간" 수치를 대조 없이 확정 보고

## 무엇을 했는가

USB CCTV 8.4시간 내구 데이터를 분석해 사용자에게 카메라별 "정지구간(delta=0) = 4 / 8 / 4 / 6 / 2 / 2" 를
표로 보고했다. 수치는 `soak_samples.csv` 의 `*_rendered_delta` 열에서 0 인 표본을 센 값이다.

## 무엇이 잘못이었나

보고한 정지 구간 수치가 전부 틀렸다. 실제 정지 구간은 **전 카메라 0건**이다.

- `main_window._report_display_stats` 는 보고 구간(60초) **증분**을 `.../cam0/image_raw=23.4fps/1435f` 형식으로 찍는다.
- 그런데 `soak_stats.parse_display_line` 과 `soak_monitor` 는 그 값을 **누적**으로 간주해 한 번 더 차분했고,
  `summarize_display` 는 "연속 두 값이 같으면 정지"로 셌다. 즉 "두 구간의 렌더 프레임 수가 우연히 같음"을
  "정지"로 오판한 것이다.
- 같은 로그 안에 독립 검증 수단(뷰어 자신이 delta==0 일 때 남기는 `no frames rendered` WARN)이 있었고
  그 건수는 0 이었다. **대조하지 않고 확정형으로 보고**했다.

어긴 규칙: `docs/claude_guideline/coding/coding.md` §5 검증 (never-self-approve, 증거 없는 완료 선언 금지),
`docs/claude_guideline/issue_fix/issue_fix.md` §룰 3 "증거 의무 — 추측 금지".

## 사용자 지적

사용자 지적 전에 자체 발견했다. 리부팅 원인 확인 중 `viewer.log` 의 `no frames rendered` 경고가 0건임을
확인하면서, 직전에 보고한 "정지 구간 4~8건" 과 모순됨을 인지해 재검증했다.

## 원인 분석

INDEX §메타 패턴의 `verify-skip` 4연속과 같은 뿌리다: **자기가 만든 도구의 출력을 검증 없이 신뢰**했다.
로그 생산자(`main_window`)와 소비자(`soak_stats`)를 같은 세션에서 30분 간격으로 작성했음에도 필드 의미
(증분 vs 누적)를 대조하지 않았고, 파서 docstring 에 "frames"(누적 뉘앙스)라고 적어놓은 것이 오독을 굳혔다.
독립 교차검증 수단(뷰어 WARN)이 이미 로그에 있었는데 보고 전에 보지 않은 것이 결정적이다.
강제 관점에서는, 수치를 사용자에게 보고하기 전 "같은 사실을 다른 경로로 한 번 더 재도출" 하는 절차가
저장소에 없다(`checks/` 미설치 환경).

## 재발 방지

강제 메커니즘 보강:

1. **필드 의미를 코드에 못박음** — `soak_stats.py:19-24` 주석에 "증분이며 누적이 아니다" 를 명시하고,
   반환 키를 `frames` → `frames_delta` 로 개명해 오독 시 즉시 KeyError 로 깨지게 했다(조용한 오판 차단).
2. **정지 판정을 0 여부로 교체** — `summarize_display` 는 연속 값 비교가 아니라 `frames_delta == 0` 으로
   센다. 아울러 `min_frames_delta` 를 요약에 추가해 "최악의 1분"이 수치로 드러나게 했다.
3. **회귀 테스트 추가** — `test_summarize_display_equal_deltas_are_not_stalls` 가 "증분이 연속으로 같아도
   정지가 아님" 을 고정한다. 이 오판이 코드로 되살아나면 테스트가 깨진다(12 passed 확인).

교차검증 원칙: 로그 파생 수치를 보고할 때는 **같은 로그의 독립 지표**(여기서는 뷰어 자체 WARN)와
반드시 대조한 뒤 보고한다. 이번 정정은 그 대조로 잡혔다.
