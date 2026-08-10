# 2026-08-10 — x86 전력 감시 추가: powercap(RAPL) 누적 에너지 차분

> 수정 이력의 기록처. 주석은 현재 코드의 사실만 담고 이력은 여기와 커밋 메시지가 담는다
> (`conventions.md:26`). **본 폴더는 패키지 안에 있어 두 저장소(LGIT MOMA · Ford-CATL Big-AMR)로
> 함께 따라간다** — 트리를 하나로 유지하는 이식 결정(ADR-002 §Decision 1)과 같은 이유다.

- 사용자 지시: 2026-08-10 "원격에 진행헀음 확인하고 개선해주세요" → "해보세요"
- 사전승인: `LGIT-C6-MOMA/docs/adr/ADR-004-system-health-rapl-power.md` (Status: Proposed)
- 배경: 이식 대상(x86_64)에 INA3221 이 없어 전원 항목이 통째로 비어 있었다(ADR-002 §Decision 4).

## 무엇을 바꿨나

| 파일 | md5(전 → 후) | 변경 |
| --- | --- | --- |
| `system_health/sysfs.py` | `4d10900f` → `be07fdc8` | `EnergyCounter` · `read_energy_counters(root=None)` · `power_watts(prev,cur,elapsed_s)` 추가, 전역 `_POWERCAP_ROOT`·`_UJ_PER_J` |
| `system_health/sampler.py` | `7334e8a6` | `SampleState.energy` 필드 추가, `collect()` 가 차분해 `record["power_w"]` 기록 |
| `system_health/report.py` | `32e45677` | ⑤ 자원 추이에 `패키지전력(W)`·`DRAM전력(W)` 계열 추가 |
| `test/test_sysfs.py` | — | RAPL 회귀 6건 |

record 스키마는 **키 추가**뿐이다(`power_w`) — 기존 로그·보고서와 호환된다. 기존 `power`
(INA3221 의 mV/mA/mW)와는 별개 키다.

## 왜 이렇게 했나

- **누적 에너지 차분** — `energy_uj` 는 순간 전력이 아니라 증가 카운터다. 스왑 활동량·CAN
  에러율과 같은 구조로 두 표본을 빼서 W 를 낸다. 누적값을 그대로 실으면 스왑 *사용량* 기준이
  표본 97 %를 WARN 으로 만든 실패를 반복하게 된다.
- **되감김 보정** — `max_energy_range_uj` 실측 `262,143,328,850 μJ`(≈262 kJ). 유휴 실측 3.68 W
  기준 약 19.8시간마다 되감기므로 상시 감시는 반드시 겪는다. 보정 없이는 그 주기에 음수 전력이
  나온다. `max_range` 를 못 읽은 도메인은 그 주기를 버린다.
- **판정하지 않는다** — 이 장비의 정상 전력 대역을 모른다. 기준선 없이 임계를 지어내면 경보
  피로만 만든다(DDS 세그먼트 수와 같은 판단).
- **주입 가능한 root** — 실경로는 권한이 닫히면 판독이 막혀 파서를 검증할 수 없다. 시험이 가짜
  트리를 넣을 수 있게 인자로 뺐다.

## 실측 확인

```
개발 PC(권한 닫힘)   power_w 키 미기록 — 조용히 비움(다른 reader 와 같은 관대함)
실기 lgit-c6-4       power_w = {core 2.35, dram 0.26, package-0 3.78, uncore 0.0} W
                     직접 판독 대조: package-0 3.68 W (2초 차분) — 일치
pytest               220 → 226 passed (신규 6건)
index-fresh · dup-signature · banned-pattern · format · adr-fields   전부 ✓
review-claim-lint(소스·문서)                                          FAIL 0
함수표 앵커 111행 소스 대조                                            일치 111 / 불일치 0
3자 md5(개발 PC ↔ 상류 ↔ 실기)                                         동일
```

## 전제 — 판독 권한 (코드 밖)

커널은 `energy_uj` 를 기본 `-r-------- root root`(0400)로 잠근다(PLATYPUS 부채널,
CVE-2020-8694/8695). 이 장비는 2026-08-10 사용자가 개방했다:

```
groupadd powermon · usermod -aG powermon tc
chgrp powermon /sys/class/powercap/intel-rapl:*/energy_uj
chmod 0440    /sys/class/powercap/intel-rapl:*/energy_uj
systemctl restart amr-health-sampler      # 보조 그룹은 기동 시점에 확정된다
```

결과: `root:powermon 0440`, 서비스 프로세스 `Groups:` 에 1003 포함(실측). **udev 규칙은 아직
없어 재부팅하면 0400 으로 돌아갈 수 있다** — 영구화가 필요하면 별건으로 규칙을 넣어야 한다.

## 되돌림

`EnergyCounter`·`read_energy_counters`·`power_watts` 와 `collect()` 의 `power_w` 기록을 제거하면
이전과 동일해진다. 로그 스키마는 키 추가뿐이라 기존 자산과 호환된다. 권한 원복은 ADR-004
§Rollback 참조.

## 남은 것

- **상시 서비스 반영**: 도는 프로세스는 기동 시점 코드를 쓰므로 `sudo systemctl restart
  amr-health-sampler` 가 필요하다(파일 동기화만으로는 붙지 않는다).
- **재부팅 후 권한 유지**: udev 규칙 미적용.
- **임계 도입 여부**: 시험 운전으로 정상 대역을 본 뒤 별도 결정.
