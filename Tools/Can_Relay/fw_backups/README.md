# fw_backups — 판다(panda) 펌웨어 롤백 자산 매니페스트

> 작성 2026-07-27 (KST), 기록 감사(A09) 산출물. 이 디렉터리에는 매니페스트가 없어 각 파일이
> **어느 빌드·어느 소스 스냅샷과 짝인지 확인할 근거**가 없었다. 아래는 그 공백을 메운 실측 기록이다.
> 원칙: **바이너리·파일명은 변경하지 않았다.** 값(해시·크기)은 재계산으로 얻은 실측치다.

---

## 1. 파일명 접미사 규약 — **두 가지가 섞여 있다 (⚠ 함정)**

같은 디렉터리인데 접미사의 **해시 기준이 서로 다르다.** 이것이 "라벨이 파일 해시와 안 맞는다"는
오해의 원인이므로 먼저 명시한다.

| 파일 | 접미사 | 접미사의 실제 기준 | 검증 |
| --- | --- | --- | --- |
| `panda.bin.signed.emulate_prefreeze_5d342ae5` | `5d342ae5` | **파일 전체 md5** 앞 8자리 | md5 = `5d342ae54bb8cf6ad769483ef0be613e` ✅ 일치 |
| `panda.bin.signed.freeze_v1_39e9bfc2` | `39e9bfc2` | **RSA 서명 꼬리 128B 의 md5**(= 판다가 보고하는 `get_signature()` 의 md5) 앞 8자리 | `md5(파일[-128:])` = `39e9bfc2b075493a9b79ba19f78055dd` ✅ 일치 |

**근거(파일:줄)**
- 플래시 검증 스크립트가 쓰는 sig 정의: `~/.claude/file-history/bd039508-6d9b-4a64-9b9c-09f973375d23/5457efd4e8a667b0@v2:13-14,32,46`
  — `sigmd5(x)=md5(bytes(x))`, `newsig = md5(b[-128:])`, `print("flash 후 sig", sig, "=> new fw 일치?", sig == newsig)`.
- 실제 플래시 로그: `docs/user_instructions/session_log.md:28`
  — `flash 후 version: DEV-d98bc1a5-DEBUG` / `flash 후 sig : 39e9bfc2b075493a9b79ba19f78055dd` /
  `=> new fw 일치? True` / `=== OK: freeze 빌드 플래시 확인 ===`
  (동일 원문: `docs/user_instructions/user_instructions.md:279`)

→ **`freeze_v1_39e9bfc2` 라벨은 근거 있음**(플래시 당시 판다 보고 sig 와 이 파일의 서명 꼬리 md5 가
정확히 일치, 내부 버전 문자열도 `DEV-d98bc1a5-DEBUG` 로 로그와 일치).
2026-07-27 감사 초기 보고의 "**라벨 출처 미상**" 판정은 **철회한다** — 파일 전체 md5(`889ee5a2`)와
비교했기 때문에 생긴 오판이었다.
**남은 실제 결함은 "라벨 근거 없음"이 아니라 "한 디렉터리에 해시 기준 2종 혼용"이다.**

---

## 2. 파일별 실측 (2026-07-27 재계산)

| 파일 | 크기 | md5 (전체) | sha256(앞16) | 내부 버전 문자열 | 서명꼬리 md5 |
| --- | --- | --- | --- | --- | --- |
| `panda.bin.signed.emulate_prefreeze_5d342ae5` | 48408 B | `5d342ae54bb8cf6ad769483ef0be613e` | `0eb0b1cacbe5c12d…` | `DEV-08c23b53-DEBUG` | `c74b14a702ccbc3c…` |
| `panda.bin.signed.freeze_v1_39e9bfc2` | 48516 B | `889ee5a2bb49f1f7cd44e7caef21ae94` | `a55992ccd3d1dcc9…` | `DEV-d98bc1a5-DEBUG` | `39e9bfc2b075493a9b79ba19f78055dd` |
| `safety_seer_gate.h.freeze_v1_wholecache` | 원본 8557 B → 현재 10959 B (아래 주) | 원본 `00a82d092a3e44eebca5f7ed6cd3a9e2` / 현재 `d4691f0c36da4c74e47433e0d50ae608` | — | (소스, 바이너리 아님) | — |
| `usb_comms.h.emulate` | 15939 B | `1e8085fa6eb34bb5519afdef7c5bd3ab` | `eed0252616511b87…` | (소스) | — |

주) `safety_seer_gate.h.freeze_v1_wholecache` 는 **2026-07-27 감사에서 파일 끝에 `⚠ SUPERSEDED` 주석
블록만 append** 했다(코드 무변경, 기존 줄번호 `:1,:4,:7,:10,:74-79,:87` 보존). 그래서 md5 가 바뀌었다.
- 감사 전 원본 md5: `00a82d092a3e44eebca5f7ed6cd3a9e2` (8557 B)
- 감사 후 현재 md5: `d4691f0c36da4c74e47433e0d50ae608` (10959 B)

## 3. 대응 관계 / 플래시 이력 (확인된 것만)

| 항목 | 확인 내용 | 근거 |
| --- | --- | --- |
| `freeze_v1_39e9bfc2` = "freeze 빌드" | 2026-07-26 19:07 플래시 성공, 버전 `DEV-d98bc1a5-DEBUG`, sig 일치 True | `docs/user_instructions/session_log.md:28` |
| `emulate_prefreeze_5d342ae5` = emulate 판(freeze 도입 전) | 라이브 킷의 `~/Project/CAN-Relay/docking_field_kit/panda.bin.signed.bak_pre_bitrate_20260727` 과 **md5 동일**(`5d342ae5…`), 버전 `DEV-08c23b53-DEBUG` | md5 재계산(2026-07-27) |
| 커버 v3 = `8a7cd6eb` | `Tools/Can_Relay/FIELD-RECORD-2026-07-25.md` §14 "빌드" 줄(감사 전 :134 → 감사 후 :169, 미수정 사본은 `docs/can_relay/field-record-orin-nx-2026-07-25.md:134`)이 기록한 "플래시 hash `8a7cd6eb`(v3)" 는 **이 디렉터리에 없다.** 실물은 `~/Project/CAN-Relay/docking_field_kit/panda.bin.signed.cover`(md5 `8a7cd6eb6e7ba4eda6c3e20b38c59f42`) 와 `.../panda.bin.signed.bak_pre_emulate`(동일 md5) | md5 재계산(2026-07-27) |
| 각 바이너리 ↔ 소스 스냅샷(git commit) 짝 | **미확인.** 내부 버전 문자열(`DEV-08c23b53` / `DEV-d98bc1a5`)이 유일한 단서이며, 그 커밋에서 재빌드했을 때 바이트가 재현되는지 검증한 기록 없음 | — |

**판정에 필요한 측정**: 각 버전 문자열의 커밋으로 `scons -j4 board` 재빌드 → 산출 `panda.bin.signed` 의
서명 꼬리 md5 가 위 표와 일치하는지 대조(빌드 타임스탬프 등으로 전체 md5 는 다를 수 있음).

## 4. ⚠ 재플래시 전 필독 — `safety_seer_gate.h.freeze_v1_wholecache` 위험

이 백업 소스의 freeze 는 **대상 객체를 가리지 않는 전량(whole-cache) 복사**다.

- `:74-79` `seer_freeze_snapshot()` — engage 시점 캐시 **전량**을 frozen 으로 복사
- `:87` `seer_cache_reply()` — `pc_authority` 중 **무조건** frozen 에서 응답

→ `0x603F`(error code)·`0x6000`(digital in)까지 고정되어 **PC 구동 중 발생한 실제 모터 고장이 Seer 에게
은닉된다.** 해당 파일 `:26-30` 주석에는 이 조건·부작용이 없다.

현행 소스는 이를 명시적으로 금지한다:
- `Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h:139`
  — "`0x603F` error·`0x6000` digital in 은 폴되나 모션 아님 → **freeze 금지**(실 고장은 Seer 가 봐야 함)"
- 같은 파일 `:170-173` `seer_is_motion_obj()` 가 freeze 대상을 `{0x6064, 0x606C, 0x6078, 0x6041}` 로 한정,
  `:203` 이 그 객체에만 frozen 적용
- freeze 집합의 실측 근거: `docs/verified_facts/2026-07-27.md:78,85`

또한 그 백업본 `:29` 의 "추종오차 0 → motor following warning(55602) 예방" 은 **이 whole-cache 판으로
검증된 기록이 없다.** 저장소의 55602 언급은
`docs/claude-mistake/2026-07-26-001_emulate-stopvalue-false-claim.md:17,45`(55602 가 *발생했다*는 사고 실증)와
`docs/adr/2026-07-27-amr-test-gui.md:31` 뿐이다. 현행 소스도
`safety_seer_gate.h:74-81` 에서 "55602 예방(의도) — 구동 중 55602=0 실측 미완" 으로 정정돼 있다.

**→ 롤백 보관용으로만 유지. 재플래시는 위 은닉 위험 인지 + 구동 중 실고장 노출 여부 실측 후에만.**

## 5. 부채 id 참조 주의

`safety_seer_gate.h.freeze_v1_wholecache:1,4,7` 주석의 `debt-002`(전환 커버)는 현행
`docs/debt/registry.md:8`(= IMU `base_link→imu_link` static TF)과 **다른 항목**을 가리킨다.
CAN relay 부채는 레지스트리에 등록이 확인되지 않는다. **미판정 모순**이며 번호를 임의로 바꾸지 말 것
(상세: `Tools/Can_Relay/FIELD-RECORD-2026-07-25.md` §11).

---

## 6. 신규 백업 추가 시 규약 (제안)

1. 파일명 접미사는 **파일 전체 md5 앞 8자리**로 통일하고, 서명 sig 는 이 README 표에 별도 열로 적는다.
2. 추가와 동시에 위 §2/§3 표에 **행을 append**(덮어쓰기 금지): 크기·md5·sha256·내부 버전 문자열·
   서명 꼬리 md5·플래시 일시·플래시 로그 위치.
3. 대응 소스 스냅샷(git commit)과 재빌드 재현 여부를 함께 기록한다.
