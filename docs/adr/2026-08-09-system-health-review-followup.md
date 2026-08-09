# ADR 2026-08-09 — `system_health` 코드 리뷰 권고 반영 (입력 검증 · 보고 정확성 · 이식성)

## Status (상태)

Proposed — 2026-08-09. 구현·전체 회귀(`pytest`) 완료, **최종 verdict 는 저자가 찍지 않는다**
(coding.md §5 never-self-approve). 외부 lane 리뷰 대기.

## Context (배경)

`docs/code_review/system_health/2026-08-07.md` 가 `REQUEST CHANGES` 로 High 1 · Medium 5 · Low 9 를
냈고, 사용자 지시(2026-08-09 "권고안대로 수정해주세요")로 그 **권고 전부**를 반영한다.

리뷰가 실측으로 확인한 사실 중 본 결정을 좌우한 것:

- 임계값 파일에 잘못된 **타입**을 넣으면 로드는 통과하고 첫 판정에서 `TypeError` 로 죽는다.
  유닛이 `Restart=always`/`RestartSec=5` 라 5초 주기 재시작 루프가 되고 기록이 0이 된다.
- `--interval 0`·음수에서 3초에 표본 757개(로그 996 KB)를 쏟는다 — "관측이 대상을 바꾸면 안 된다"
  (`sysfs.py:7-8`)는 설계 원칙을 감시기 자신이 깬다.
- `--since` 를 쓰면 ⑥ 로그 성장률이 2.5배로 부풀려진다(표본당 119 B → 298 B). 이 수치가
  `--max-total-mb` 를 정하는 근거라 과대 추정이 곧 운영 판단 오류다.
- `install_service.sh:20` 이 `REPO` 를 `/home/nvidia/...` 로 하드코딩해, 다른 PC 로 이식한 사본에서
  `--apply` 하면 존재하지 않는 경로를 향한다. 본 패키지는 지금 개발 PC 로 이식된 상태다.

## Decision (결정)

### 1. 설정 오류는 **로드 시점에** 거부한다

`Thresholds.from_mapping` 이 키뿐 아니라 **값**도 검증한다 — ①필드 타입(수치 필드에 문자열·bool 거부,
Optional 필드는 `None` 허용) ②WARN/ERROR **대소 순서**(높을수록 나쁨: `warn <= error`, 낮을수록 나쁨:
`warn >= error`). 위반은 `ValueError`. `sampler.run()` 이 이를 `SystemExit` 로 바꿔 journald 에
한 줄로 남긴다 — 스택 트레이스가 아니라 고칠 대상을 보여준다. 기존 `KeyError`(미지·폐기 키) 계약은
그대로 둔다.

### 2. CLI 인자는 **범위를 검증**한다

`sampler`: `--interval > 0`, `--max-total-mb > 0`, `--max-age-days > 0`, `--top-rss >= 0`,
`--proc-scan-every >= 0`. `report`·`webview`: `--interval > 0`. 위반은 `argparse` 표준 경로(exit 2).
방어적으로 `gap_stats` 는 `interval_s <= 0` 이면 통계를 내지 않고 빈 결과를 돌려준다.

### 3. 주기는 **절대 시각** 기준으로 잡는다

`_sleep_until(now + interval)` → 기준선에서 `n·interval` 로 계산한 마감시각. 지연이 한 주기를 넘으면
그 주기는 건너뛴다(따라잡기 폭주 금지). 실측 드리프트 +7.3 ms/주기(목표 1 s)를 제거한다.

### 4. 보고서는 **분자와 분모의 구간을 일치**시킨다

`--since` 가 있어도 ⑥ 로그 성장률은 **전 구간 표본 수**를 분모로 쓰고 "전 구간 기준" 라벨을 붙인다.
`report.main` 은 로그를 1회만 완독하고 그 결과를 `format_report` 에 주입한다(공개 API 변경 — §Consequences).
`/api/report` 는 최근 `REPORT_MAX_SAMPLES=5000` 표본으로 상한을 두고, 상한이 걸리면 보고문에 명시한다.

### 5. 설치 스크립트는 **자기 위치에서 저장소 경로를 유도**한다

`REPO` 를 `HERE/../../..` 로 계산한다. 유닛 파일은 `@REPO@`·`@USER@`·`@GROUP@` 자리표시자를 쓰는
템플릿으로 두고, `install_service.sh` 가 설치 시점에 치환한다. 사용자·그룹은 `id -un`/`id -gn` 로
채운다 — 경로만 고쳐도 `User=nvidia` 때문에 다른 PC 에서 기동하지 못하기 때문이다.

### 6. 대시보드는 **로그 문자열을 이스케이프**하고 등급 표는 **한 곳에서만** 정의한다

브라우저 JS 에 `esc()` 를 두어 경보 키·메시지·레일 이름·존 이름을 삽입 전에 이스케이프한다.
등급→아이콘·라벨 매핑은 Python `LEVEL_VIEW` 를 단일 근원으로 삼아 페이지 서빙 시 주입한다(JS 리터럴
중복 제거).

### 7. 코어별 CPU 사용률은 **코어 번호로 join** 한다

`CpuSnapshot` 에 `core_ids` 필드(기본 빈 튜플)를 더하고, 양쪽에 번호가 있으면 번호로 짝짓는다.
없으면 종전대로 인덱스로 짝짓는다(하위 호환). ⚠ 이 결정의 전제(코어 offline 시 `/proc/stat` 행이
사라진다)는 **본 작업에서 실측하지 않았다** — 번호 join 은 전제가 거짓이어도 결과가 같으므로
무해한 방향으로만 바꾼다.

### 8. 잔여 정리

미사용 상수 `_PROC_STAT_UTIME`·`_PROC_STAT_STIME` 삭제, `enforce_limits` 의 총량 재계산 제거(삭제분
차감), `evaluate` 의 지역명 `rate` 를 `swap_rate`·`can_rate` 로 분리, `setup.py` `data_files` 에
webview 유닛 추가.

## Consequences (영향)

**얻는 것**

- 잘못된 임계값 파일이 **기동 시** 한 줄 메시지로 거부된다 — 재시작 루프로 기록이 사라지는 최악 경로 제거.
- 감시기가 감시 대상의 부하가 되는 인자 조합이 차단된다.
- `--since` 보고서의 성장률이 실제와 일치한다. `report` CLI 의 로그 완독이 2회 → 1회.
- 이식한 사본에서 `install_service.sh --apply` 가 **그 사본의 경로**로 설치된다.

**치르는 비용 / 남는 위험**

- **공개 API 변경 2건**: `format_report` 에 키워드 전용 인자 `records`·`files`·`max_samples` 추가
  (기존 위치 인자 순서·기본 동작 불변), `CpuSnapshot` 에 기본값 있는 필드 `core_ids` 추가.
  둘 다 기존 호출부·테스트를 깨지 않는다(전체 회귀로 확인).
- **거부가 늘어난다**: 지금까지 통과하던 임계값 파일(문자열 수치·역전된 warn/error)이 이제 기동을
  막는다. 의도된 변경이며, 메시지에 어느 키가 왜 거부됐는지 적는다.
- 유닛 파일이 자리표시자를 갖게 되어 **소스 트리의 `.service` 를 그대로 `systemctl` 에 넣으면 안 된다**
  — 반드시 `install_service.sh` 를 거쳐야 한다. 파일 상단 주석에 명시했다.
- `/api/report` 상한(5000)은 그보다 오래된 구간을 보고서에서 제외한다. 전 구간이 필요하면 CLI 를 쓴다.

## Rollback (되돌림 계획)

가역이다. 되돌리는 절차:

1. 코드: 본 ADR 로 변경된 파일을 리뷰 시점 해시로 복원한다 —
   `sysfs.py` `bc9ae8ef` · `sampler.py` `bc5f7b0d` · `thresholds.py` `2da7d7ac` ·
   `report.py` `557ca9d0` · `webview.py` `156cf164` · `ringlog.py` `0fa272fa` · `setup.py` `29a54b9d` ·
   `install_service.sh` `c9462401` · `systemd/*.service` `5efae91b`·`37bd1752`
   (`docs/code_review/system_health/2026-08-07.md` §코드 버전).
2. 운영: 이미 설치된 유닛은 `./install_service.sh --remove both` 후 복원한 스크립트로 재설치.
   **로그·임계값 파일은 삭제하지 않는다**(스크립트가 보존한다).
3. 영속 상태 변경 없음 — 로그 스키마·JSONL 필드는 바뀌지 않는다.

## 관련 문서

- 리뷰: `docs/code_review/system_health/2026-08-07.md` (High 1 · Medium 5 · Low 9)
- 선행 ADR: `docs/adr/2026-07-28-system-health-monitor.md`,
  `docs/adr/2026-08-01-system-health-phase3-sw-watchdog.md`
