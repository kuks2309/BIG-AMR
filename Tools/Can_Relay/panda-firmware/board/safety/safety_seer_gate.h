// *** Seer 게이트 safety 모드 (도킹 릴레이) + 전환 커버 (debt-002) ***
// bus0 = Seer, bus2 = 모터. pc_authority 시 Seer SDO 쓰기(0x601~604, 0x23/27/2B/2F) drop +
// 가짜 ack(0x580+N: 60 idxlo idxhi sub 0..) 합성, 읽기(0x40)·guard(RTR)·응답은 통과.
// 전환 커버(debt-002): 0xe8 engage 후 SEER_COVER_US 동안, 릴레이 스위치로 CAN2(모터)가 회복(~150ms)
//   하는 사이 판다가 캐시된 모터 응답으로 Seer read/guard/write에 대신 답해 Motor timeout(52111)/
//   odo lost(52106) 방지. Seer(CAN0)는 항상 판다 bus0에 연결, 정차 중이라 캐시값이 곧 정확값.
//   근거: docs/can_relay/field-record-orin-nx-2026-07-25.md §13, debt-002, PCAN make_seer_gate_hook 이식.
//
// ⚠⚠ 감사 정정 (2026-07-27, 기록감사 A06) — 위 :2~:6 서술은 부정확하다. 원문은 이력으로 남기고
//    아래를 정본으로 읽을 것. 코드·상수는 변경하지 않았다(정정은 서술 한정).
//  (1) [:2~:3 정정 — 모순] "0x23/27/2B/2F drop", "응답은 통과" 둘 다 코드와 다르다.
//      실제: seer_gate_fwd_hook() bus_num==0 분기는 `if (cmd == 0x40U)` 외 **모든** 0x601~604
//      프레임을 else 로 보내 seer_fake_ack() 후 bus_fwd=-1 한다 → abort(0x80)·세그먼트(0x60/0x70)
//      까지 drop 되고 0x60 정상 ack 이 합성된다. 또 조건은 pc_authority 단독이 아니라
//      `emulate = cover || pc_authority` 이므로 pc_authority=false 인 300ms 전환 커버 구간
//      (disengage 포함, usb_comms.h:406-408 이 0xe8 값과 무관하게 커버를 건다)에서도 쓰기가 drop 된다.
//      "응답 통과"도 emulate 중엔 거짓: bus_num==2 분기가 모터 실응답(0x581~584)·guard 응답
//      (0x701~704)을 Seer 로 forward 하지 않고(bus_fwd=-1) 캐시/guard 캐시가 대신 답한다.
//      → 정정: "읽기(0x40)·guard(RTR)는 모터로도 forward 되나, emulate 중 모터 실응답은 Seer 로
//        suppress 되고 캐시/스냅샷이 대신 응답한다. 응답이 그대로 통과하는 것은 비-emulate 시뿐."
//      (본문 주석 "모터 실응답은 … Seer로는 suppress" 가 :3 과 상충했음 — 본문 쪽이 맞다.)
//  (2) [:4 정정 — 인용 절단] 회복시간의 원 실측은 범위값이다:
//      docs/can_relay/field-record-orin-nx-2026-07-25.md:129 "engage 시 bus2 RX 수신에러
//      (REC 100~237)→error_passive→**~150~220ms 회복**". 하한만 인용하면 300ms 커버 마진이
//      실제보다 넉넉해 보인다. 또 이 값은 engage 실측이며, disengage 의 모터 회복시간은
//      **미측정 과제**로 남아 있다(같은 문서 :139).
//  (3) [:5 조건 누락] 52111/52106 방지의 검증 범위는 **engage 한정**이다.
//      field-record …-2026-07-25.md:137 "engage(도킹 진입) = 완전 해결: 반복 8/8 … 52111/52106 = 0".
//      같은 문서 :139 "**disengage = 미해결** … 판다 루프 밖이라 커버 한계(300ms 고정·자동종료
//      둘 다 실패)". → disengage 에서는 동일 300ms 커버로 방지가 실증되지 않았다.
//      SEER_COVER_US 값은 이번 감사에서 변경하지 않았다.
//  (4) [:6 조건 누락] "정차 중이라 캐시값이 곧 정확값"은 **전환 커버(300ms, 정차 도킹 순간)**
//      에만 성립하는 정당화다(원 근거 field-record …-2026-07-25.md:133 도 커버 윈도우 문맥 한정).
//      그러나 `emulate = cover || pc_authority` 이므로 캐시 대리응답은 PC 주도 구동 전 구간
//      (=비정차)에도 지속된다. 코드 어디에도 정차 확인 게이트가 없다(pc_authority 에지 처리에
//      상태 검사 없음). 이 전제가 깨지기 때문에 별도 freeze 로직(아래 "정지값 고정")이 필요했다.
bool pc_authority = false;  // 0xe9 AUTH_SET: false=Seer 투명중계, true=PC 주도(게이트 ON)

// *** Seer 호밍 트리거 차단 (0xec) ***
// 제어권 반환 직후 Seer 가 자기 초기화로 0x60FB.4=1(RstStart)을 보내 조향축을 137° 왕복시킨다.
// 이 플래그가 서면 **Seer 가 보내는 호밍 트리거만** 골라 drop 하고 가짜 ack 로 답한다.
// 기본값 false = 종전 거동 유지(차단 안 함). 호스트가 필요할 때만 켠다.
bool seer_block_homing = false;

// Seer→모터 SDO 쓰기 중 '호밍을 일으키는' 프레임인지 판정한다.
//   0x60FB sub4 = RstStart (0=off / 1=on)   [Handbook V7.0 §6.9 page 171]
//   0x6098      = Homing method             — 드라이브 상주 설정이라 임의 변경을 막는다
// SDO expedited write cmd: 0x2F(1B) 0x2B(2B) 0x27(3B) 0x23(4B)
static bool seer_is_homing_write(CANPacket_t *f) {
  uint8_t cmd = f->data[0];
  if ((cmd != 0x2FU) && (cmd != 0x2BU) && (cmd != 0x27U) && (cmd != 0x23U)) { return false; }
  uint16_t index = (uint16_t)(f->data[1] | ((uint16_t)f->data[2] << 8));
  uint8_t sub = f->data[3];
  if ((index == 0x60FBU) && (sub == 0x04U)) { return true; }
  if (index == 0x6098U) { return true; }
  return false;
}

#define SEER_COVER_US 300000U           // 전환 커버 지속(μs) = 300ms (engage/disengage 공통 고정)
uint32_t seer_cover_until_us = 0U;      // usb_comms.h 0xe8 시 설정(engage·disengage 모두)

#define SEER_CACHE_N 24                 // Seer 읽기객체 5*4node=20 + 여유
typedef struct {
  uint8_t valid;
  uint8_t node;
  uint16_t index;
  uint8_t sub;
  uint8_t data[8];
} seer_resp_cache_t;
seer_resp_cache_t seer_cache[SEER_CACHE_N];
uint8_t seer_guard_data[5][8];
uint8_t seer_guard_len[5] = {0};
uint8_t seer_guard_valid[5] = {0};

// *** 정지값 고정(freeze) — PC 구동을 Seer 에게 숨김 ***
// pc_authority(도킹/구동) engage 시점의 캐시(정차 상태)를 스냅샷으로 잡고, 구동 중 Seer 폴에
// 이 스냅샷을 고정 응답한다. → PC 가 모터를 실제 구동해 실위치(0x6064)·statusword 가 변해도
// Seer 는 engage 시점 "정지" 상태만 읽음 → 추종오차 0 → motor following warning(55602) 예방.
// release 시 해제하여 실시간 캐시로 복귀(Seer 직결 정상). 근거: docs/claude-mistake/2026-07-26-001.
//
// ⚠ 감사 정정 (2026-07-27, A06) — 위 서술의 조건 누락·미검증 단정을 아래로 보정한다.
//  (5) [조건] "구동 중 Seer 는 engage 시점 정지 상태만 읽음"은 **engage 시점에 그 객체가 이미
//      캐시돼 있을 때만** 참이다. seer_freeze_snapshot() 은 캐시 내용과 무관하게
//      seer_frozen_valid=1 로 세우고, seer_cache_reply() 는 frozen 에서 매치를 못 찾으면
//      chosen 을 **실시간 캐시 항목으로 둔 채 그대로 전송**한다(폴백 경고 없음)
//      → 미캐시 객체는 PC 구동 중 실위치가 Seer 로 나간다. 이 조용한 폴백이 곧 과거
//      실위치 누설·55602 사건의 메커니즘이다(docs/claude-mistake/2026-07-26-001_emulate-stopvalue-false-claim.md:17-19).
//      스냅샷 시점 = pc_authority 상승에지 = usb_comms.h:410-411(0xe9) 직후 첫 fwd 프레임인데,
//      호스트 take 순서는 "safety_mode 30 → CAN0/2 enable → 0xe9=1 → 0xe8=1"
//      (docs/user_instructions/sessions/56a709a5-93b4-4ff8-875b-bdf3f029c7eb.md:87)이라
//      **캐시 워밍 전에 스냅샷이 잡힐 수 있다**. 저빈도 객체는 12초에 66회(≈5.5Hz,
//      docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md:61,64)라 워밍에 수백 ms 가 필요하다.
//      판정에 필요한 측정: "safety_mode 30 설정 후 0xe9 까지의 지연" vs "폴 객체 전량 캐시 충전 시간" 실측.
//  (6) [미검증] "→ 추종오차 0 → 55602 예방"은 **설계 의도**이며 현재 빌드(0x6041 추가본)에 대한
//      구동 실측 근거가 없다. 인용된 docs/claude-mistake/2026-07-26-001…:16-19 은 55602 가
//      "발생했다"는 사고 기록이지 예방 실증이 아니다. 예방 검증은
//      docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md:89 에 "freeze 정정 검증: 제어권 획득 후
//      저속 구동 중 Seer 알람 0 확인(검증 계단 ③ 시점에 수행)"으로 **미수행 예정** 상태이고,
//      해당 ADR 자체가 :3 Status: Proposed 다. docs/issues_and_fixes/issues_and_fixes.md:11(및 :13)
//      의 "완료" 근거도 비트레이트(전원사이클·errors=[]·rx_errs=0)뿐으로 구동 중 55602 항목이 없다.
//      → "55602 예방(의도) — 구동 중 55602=0 실측 미완, ADR §Verification:89 로 수행 예정".
seer_resp_cache_t seer_frozen[SEER_CACHE_N];
uint8_t seer_frozen_valid = 0U;

static void seer_send_bus0(uint32_t sndaddr, const uint8_t *d, uint8_t len) {
  CANPacket_t p;
  p.rtr = 0U; p.returned = 0U; p.rejected = 0U; p.extended = 0U;
  p.bus = 0U;
  p.addr = sndaddr;
  p.data_len_code = len;
  for (int i = 0; i < 8; i++) { p.data[i] = (i < (int)len) ? d[i] : 0U; }
  can_send(&p, 0U, true);
}

static void seer_cache_store_resp(CANPacket_t *r) {
  uint8_t cmd = r->data[0];
  if ((cmd != 0x43U) && (cmd != 0x47U) && (cmd != 0x4BU) && (cmd != 0x4FU)) { return; }
  uint8_t node = (uint8_t)(GET_ADDR(r) - 0x580);
  uint16_t index = (uint16_t)(r->data[1] | ((uint16_t)r->data[2] << 8));
  uint8_t sub = r->data[3];
  int match = -1;
  int free_slot = -1;
  for (int i = 0; i < SEER_CACHE_N; i++) {
    if (seer_cache[i].valid != 0U) {
      if ((seer_cache[i].node == node) && (seer_cache[i].index == index) && (seer_cache[i].sub == sub)) {
        match = i;
        break;
      }
    } else if (free_slot < 0) {
      free_slot = i;
    } else {
      // occupied slot with no match yet
    }
  }
  int slot = (match >= 0) ? match : free_slot;
  if (slot >= 0) {
    seer_cache[slot].valid = 1U;
    seer_cache[slot].node = node;
    seer_cache[slot].index = index;
    seer_cache[slot].sub = sub;
    for (int i = 0; i < 8; i++) { seer_cache[slot].data[i] = r->data[i]; }
  }
}

static void seer_freeze_snapshot(void) {
  // engage 시점의 캐시(정차값) 전량을 frozen 으로 복사. 이후 구동 중엔 이 값만 Seer 에 응답.
  for (int i = 0; i < SEER_CACHE_N; i++) {
    seer_frozen[i] = seer_cache[i];
  }
  seer_frozen_valid = 1U;
}

// 모션 노출 객체 — 이것만 정지 스냅샷으로 치환한다.
// 근거: 2026-07-27 Seer SDO 폴 12초 실측(bus0 0x601~604, cmd 0x40 인덱스 집계).
//   0x6064 위치        노드당 2718~2920회  → freeze 필수
//   0x6041 statusword  node3/4 300여·node1/2 66회 → freeze 필수 (구동 중 상태비트가 변함)
//   0x6078 전류        66회                → freeze 필수
//   0x606C 실속도      0회(Seer 미폴)      → 현재 죽은 분기지만 모션 노출 객체이므로 유지
//   0x603F error·0x6000 digital in 은 폴되나 모션 아님 → **freeze 금지**(실 고장은 Seer 가 봐야 함)
// ⚠ 정정 이력: 종전 소스에 0x6041 이 빠져 있었다. 그대로 두면 PC 구동 중 Seer 가 실제
//   statusword 변화를 보게 된다. 운영 기록(메모리 biguamr-motor-node4-sign-crab)의
//   {0x6064, 0x6078, 0x6041} 이 옳았고 실측으로 확정했다.
//   ADR: docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md
//
// ⚠ 감사 정정 (2026-07-27, A06) — 위 근거 표기·"확정" 서술을 아래로 보정. 객체 목록은 미변경.
//  (7) [근거 인용 보정] 위 "12초 실측" 수치의 1차 캡처 로그는 **저장소에 보존돼 있지 않다**
//      (Log/ 에 해당 캡처 없음). 수치가 실재하는 곳은 2차 서술 2곳뿐이다:
//      docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md:55-64(12초 스니핑 표),
//      docs/issues_and_fixes/issues_and_fixes.md:11. 두 기록의 0x6041 표기도 서로 다르다
//      (ADR:60 "node3/4 300여, node1/2 66" vs issues_and_fixes:11 "66~312회").
//      프로젝트 규칙(docs/claude-mistake/2026-07-27-001_freeze-object-list-guessed.md:42-43
//      "모든 객체 인덱스·상수는 캡처데이터 또는 1차문서 라인 인용을 코드 주석에 병기")에 따라
//      근거를 위 줄 단위 인용으로 대체한다. 재현 시 원 캡처를 Log/ 에 보존할 것.
//  (8) [미판정 모순 — 0x606C] 구현 집합은 0x606C 포함 **4개**이고 ADR:72 는 "0x606C 는 …
//      모션 노출 객체가 맞으므로 유지"로 결정했다. 반면
//      docs/claude-mistake/2026-07-27-001_freeze-object-list-guessed.md:44-45 (frontmatter
//      status: open, :5)는 "freeze 객체를 {0x6064, 0x6078, 0x6041}(0x606C 제거·0x6041 추가)로
//      수정 예정"이라 명시하고 같은 문서 :25 는 0x606C 를 "오포함"으로 판정한다.
//      → 두 기록 불일치, **미판정**. 이번 감사에서 seer_is_motion_obj() 목록은 변경하지 않는다.
//      판정에 필요한 측정: Seer 가 0x606C 를 폴하는 운영 조건이 존재하는지 장시간 스니핑.
//      후속 과제: mistake 2026-07-27-001 의 status 정리(어느 결정이 유효한지 확정).
//  (9) [:0x603F/0x6000 freeze 금지 — 조건] "실 고장은 Seer 가 봐야 함"은 **모터가 계속 응답할
//      때만** 참이다. 값 수준 고장은 다음 폴에서 전달되지만, 캐시 항목에는 타임스탬프·TTL·무효화가
//      전혀 없어(seer_cache_store_resp/seer_cache: valid 는 한 번 1이 되면 내려가지 않음)
//      모터 무응답·노드 상실 시 판다는 **마지막 정상값을 무기한 계속 응답**한다
//      (emulate 중 실응답은 bus_num==2 분기에서 suppress 되고 응답은 오직 캐시에서 나옴).
//      즉 위 :5-6 이 방지 대상으로 든 52111(모터 통신 상실, 의미:
//      docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md:14) 자체를 Seer 로부터 은폐하는 방향이다.
//      캐시 TTL 도입은 **별도 제안·검증 대상**으로만 기록(이번 감사에서 코드 변경 없음).
//
// ⚠ 정정 (2026-07-27, 실기 호밍 캡처) — 위 :139 "0x6000 digital in … 모션 아님"은 과한 단정이다.
//   원문은 이력으로 남기고 아래를 정본으로 읽을 것. 객체 목록·코드는 변경하지 않았다.
//  (10) 0x6000 은 **배열 오브젝트**이고 실제 입력값은 sub 1 이다(sub 0 은 항목 수 = 2).
//      sub 1 의 비트: bit0 = ServoEnable, **bit3 = −Limit**.
//      실측(Log/homing_capture_220350.jsonl 전수 디코드, 253,510 프레임):
//        node3 0x6000.01  t=47.0249  0x01→0x09,  t=49.4223  0x09→0x01
//        node4 0x6000.01  t=47.0254  0x01→0x09,  t=49.4227  0x09→0x01
//        구동축 node1·2 는 420 폴 전량 0x01 로 무변화(조향축에서만 전이).
//      → 정정: "0x603F error·0x6000 digital in 은 폴되나 **위치/속도 노출은 아님** → freeze 금지
//        (실 고장은 Seer 가 봐야 함)." 다만 bit3 는 조향축이 음의 리밋에 도달/이탈할 때만 셋·해제되는
//        **모션의 결과 사건**이므로, 0x6000 이 아무 모션 단서도 노출하지 않는다고 읽으면 안 된다.
//        PC 구동이 조향을 리밋까지 몰 수 있는 시나리오를 허용하기 전 이 항목을 재평가할 것.
static bool seer_is_motion_obj(uint16_t index) {
  return (index == 0x6064U) || (index == 0x606CU) ||
         (index == 0x6078U) || (index == 0x6041U);
}

static void seer_cache_reply(int addr, CANPacket_t *req) {
  uint8_t node = (uint8_t)(addr - 0x600);
  uint16_t index = (uint16_t)(req->data[1] | ((uint16_t)req->data[2] << 8));
  uint8_t sub = req->data[3];
  // 수술적 freeze: 기본은 항상 실시간 캐시(Seer 응답 누락 0 → 타임아웃 회귀 불가).
  // pc_authority 중 '모션객체'만 engage 스냅샷(정지값)으로 치환 → 위치/속도만 정지로 보임.
  //
  // ⚠ 감사 정정 (2026-07-27, A06) — 위 "누락 0 / 타임아웃 회귀 불가"는 **반증됐다**(단정 무효).
  //   정정: **캐시가 채워진 객체에 한해** 즉답한다. 아래 `if (chosen != NULL)` 이므로 캐시에
  //   (node,index,sub) 항목이 없으면 Seer 에게 **아무 응답도 보내지 않고**, 그 사이 모터의
  //   실응답(0x581~584)은 seer_gate_fwd_hook() bus_num==2 분기에서 Seer 방향으로 suppress 된다
  //   → 미캐시 객체는 캐시응답도 실응답도 없어 Seer 가 **완전 무응답**을 본다.
  //   미캐시가 실제로 발생하는 경로 2개:
  //     (a) seer_cache_store_resp() 가 0x43/0x47/0x4B/0x4F 만 저장 → abort(0x80) 등은 캐시에 없음.
  //     (b) 같은 함수에 **축출 로직이 없어** 24슬롯이 모두 valid 이면 free_slot=-1 → 신규 항목 저장 실패.
  //   즉 타임아웃 회귀가 원천 차단되지는 않는다. (방지 대상 52111/52106 의 발생 메커니즘:
  //   docs/can_relay/field-record-orin-nx-2026-07-25.md:123 "in-flight SDO 트랜잭션이 깨지면
  //   Seer가 노드 상실 판단".)
  //   실제 회귀 여부 판정에 필요한 측정: engage 직후 Seer 폴 객체별 첫 응답 지연(캐시 워밍 시간),
  //   그리고 폴 집합의 distinct (node,index,sub) 개수가 SEER_CACHE_N(24)을 넘는지 실측.
  seer_resp_cache_t *chosen = NULL;
  for (int i = 0; i < SEER_CACHE_N; i++) {
    if ((seer_cache[i].valid != 0U) && (seer_cache[i].node == node) &&
        (seer_cache[i].index == index) && (seer_cache[i].sub == sub)) {
      chosen = &seer_cache[i];
      break;
    }
  }
  if ((pc_authority) && (seer_frozen_valid != 0U) && seer_is_motion_obj(index)) {
    for (int i = 0; i < SEER_CACHE_N; i++) {
      if ((seer_frozen[i].valid != 0U) && (seer_frozen[i].node == node) &&
          (seer_frozen[i].index == index) && (seer_frozen[i].sub == sub)) {
        chosen = &seer_frozen[i];
        break;
      }
    }
  }
  if (chosen != NULL) {
    seer_send_bus0((uint32_t)(0x580 + node), chosen->data, 8U);
  }
}

static void seer_fake_ack(int addr, CANPacket_t *req) {
  uint8_t d[8];
  d[0] = 0x60U;
  d[1] = req->data[1];
  d[2] = req->data[2];
  d[3] = req->data[3];
  d[4] = 0U; d[5] = 0U; d[6] = 0U; d[7] = 0U;
  seer_send_bus0((uint32_t)(0x580 + (addr - 0x600)), d, 8U);
}

static const addr_checks* seer_gate_init(uint16_t param) {
  UNUSED(param);
  controls_allowed = true;
  return &default_rx_checks;
}

static int seer_gate_tx_hook(CANPacket_t *to_send, bool longitudinal_allowed) {
  UNUSED(to_send);
  UNUSED(longitudinal_allowed);
  return true;  // PC 원발 CAN_TX 허용
}

static int seer_gate_tx_lin_hook(int lin_num, uint8_t *data, int len) {
  UNUSED(lin_num);
  UNUSED(data);
  UNUSED(len);
  return false;
}

static int seer_gate_fwd_hook(int bus_num, CANPacket_t *to_fwd) {
  int addr = GET_ADDR(to_fwd);
  int bus_fwd = -1;

  // pc_authority engage/release 에지 처리: engage 시 현 캐시(정차값)를 freeze,
  // release 시 해제(실시간 캐시 복귀). 한 번의 짧은 스냅샷 복사만 수행(ISR 부담 최소).
  static bool prev_pc_auth = false;
  if ((pc_authority) && (!prev_pc_auth)) {
    seer_freeze_snapshot();
  } else if ((!pc_authority) && (prev_pc_auth)) {
    seer_frozen_valid = 0U;
  } else {
    // 에지 없음
  }
  prev_pc_auth = pc_authority;

  // 캐시 갱신: 모터 응답(0x581~584)·guard 응답(0x701~704, rtr=0)을 어느 버스에서 보이든 최신 저장
  if ((addr >= 0x581) && (addr <= 0x584) && (to_fwd->rtr == 0U)) {
    seer_cache_store_resp(to_fwd);
  } else if ((addr >= 0x701) && (addr <= 0x704) && (to_fwd->rtr == 0U)) {
    uint8_t gn = (uint8_t)(addr - 0x700);
    uint8_t glen = (uint8_t)GET_LEN(to_fwd);
    if (glen > 8U) { glen = 8U; }
    for (int i = 0; i < 8; i++) { seer_guard_data[gn][i] = (i < (int)glen) ? to_fwd->data[i] : 0U; }
    seer_guard_len[gn] = glen;
    seer_guard_valid[gn] = 1U;
  } else {
    // no cache update
  }

  bool cover = ((int32_t)(seer_cover_until_us - microsecond_timer_get()) > 0);
  // 모범답안(모터 에뮬레이션) 지속: 전환 커버창(300ms) OR PC주도(도킹) 내내.
  // → 릴레이 작동 중 Seer 폴 전량을 캐시 모범답안으로 응답(Seer는 모터 상태·전환과 무관하게 만족).
  //   읽기/guard는 모터로도 forward해 모터를 계속 폴(살려둠)+캐시 신선도 유지. 쓰기는 가짜ack(PC/hold가 구동).
  //   모터 실응답은 캐시만 갱신하고 Seer로는 suppress(Seer는 캐시로 받음). auth=Seer(노드이동)은 투명 유지.
  bool emulate = cover || pc_authority;

  if (bus_num == 0) {  // Seer -> 모터
    if (emulate && (addr >= 0x601) && (addr <= 0x604) && (to_fwd->rtr == 0U)) {
      uint8_t cmd = to_fwd->data[0];
      if (cmd == 0x40U) {
        seer_cache_reply(addr, to_fwd);   // 읽기 → 캐시 모범답안 즉답
        bus_fwd = 2;                      // + 모터로도 폴 forward(모터 폴 유지·캐시 갱신)
      } else {
        seer_fake_ack(addr, to_fwd);      // 쓰기 → 가짜 ack
        bus_fwd = -1;                     // 모터로 안 보냄
      }
    } else if (emulate && (addr >= 0x701) && (addr <= 0x704) && (to_fwd->rtr != 0U)) {
      uint8_t gn = (uint8_t)(addr - 0x700);
      if (seer_guard_valid[gn] != 0U) {
        seer_send_bus0((uint32_t)(0x700 + gn), seer_guard_data[gn], seer_guard_len[gn]);
      }
      bus_fwd = 2;   // guard RTR도 모터로 forward(모터 guard 유지)
    } else if ((seer_block_homing) && (addr >= 0x601) && (addr <= 0x604) &&
               (to_fwd->rtr == 0U) && seer_is_homing_write(to_fwd)) {
      // 비-emulate(투명) 구간에서도 **Seer 의 호밍 트리거만** 골라 막는다.
      // 제어권 반환 직후 Seer 가 자기 초기화로 0x60FB.4=1 을 보내면 조향축이 137° 왕복한다
      // — 테스트 도구가 제어권을 넘길 때마다 로봇이 움직이면 쓸 수 없다.
      // 호밍이 필요하면 명시적으로 한다(0xea 시퀀서).
      // ⚠ 가짜 ack 를 주므로 Seer 는 호밍이 수행된 것으로 안다. 드라이브 원점은 직전 호밍
      //   결과가 유지되므로 기준 자체는 유효하나, 원점이 실제로 유실된 상황이라면
      //   Seer 가 그것을 모르게 된다. 그래서 기본값은 차단 안 함(0xec 로 켠다).
      seer_fake_ack(addr, to_fwd);
      bus_fwd = -1;
    } else {
      bus_fwd = 2;   // 투명(auth=Seer 노드이동, non-emulate)
    }
  } else if (bus_num == 2) {  // 모터 -> Seer
    if ((addr >= 0x600) && (addr <= 0x604)) {
      bus_fwd = -1;  // PC 명령 에코 차단
    } else if (emulate && (((addr >= 0x581) && (addr <= 0x584)) ||
                           ((addr >= 0x701) && (addr <= 0x704)))) {
      bus_fwd = -1;  // emulate 중: Seer는 캐시 모범답안으로 받음 → 실응답 suppress(캐시는 위서 갱신됨)
    } else {
      bus_fwd = 0;   // 투명: 모터 응답(0x580)·guard 응답(0x700) → Seer
    }
  } else {
    bus_fwd = -1;
  }
  return bus_fwd;
}

// ***************************************************************************
// *** 조향 호밍 시퀀서 (steer homing sequencer) ***
//
// 목적: pc_authority(PC 주도) 중 판다가 조향축 원점 복귀를 직접 지휘한다.
//   Seer 가 주도할 때는 Seer 가 호밍을 보내지만, PC 가 게이트를 잡으면 Seer 쓰기가
//   seer_fake_ack() 로 drop 되므로(위 seer_gate_fwd_hook bus_num==0 분기) 아무도 호밍을
//   개시하지 못한다. 이 시퀀서가 그 공백을 메운다.
//
// *** 호밍의 정의 ***
//   호밍 = "원점(리밋)까지 간다" 가 아니라 **"원점을 경유해 조향 0° 로 복귀한다"** 까지다.
//   원점은 경유지이고 종착지는 조향 0° 다. 리밋에 얹힌 채 끝내면 그 방향 지령이 막히고
//   스위치도 눌린 채 남는다. TR_Nav 도 동일하다 — 리밋을 잡은 뒤 home_offset 으로 이동해
//   거기서 끝낸다(amr_canopen_motor_driver/include/.../can_open.hpp 의 home_count_ 1→2→3).
//
// *** 본 시퀀스는 Seer 실측 시퀀스를 그대로 따른다 ***
//   Log/homing_capture_220350.jsonl (2026-07-27 판다 수동청취, 253,510 프레임) 전수 디코드:
//     t=17.910  0x6040 = 0x86        fault reset + enable
//     t=17.918  0x6099 = 2500        homing speed (0.1 r/min)
//     t=17.925  0x60FB.4 = 1         RstStart
//     t=47.03   0x6000 리밋 비트 ON  (node3·node4 동시)
//     t=49.00   0x6041 bit15 0→1     호밍 완료 = 이 지점이 원점(0)
//     t=49.03   0x6060 = 1           PP 재설정
//     t=49.05   0x6081 = 30000 / 0x6083 = 250 / 0x6084 = 250
//     t=49.14   0x607A = 7882020(node3) · 7859062(node4)   ← 조향 0°
//     t=49.14   0x6040 = 0x3F        setpoint 적용
//     t=49.42   0x6000 리밋 비트 OFF (축이 원점 밖으로 나감)
//   0x6098 은 **한 번도 쓰지 않는다** — 아래 설계 결정 (b) 참조.
//
// *** 1차 source 근거 (IxLII/IxLs/IxH Servo Driver Handbook V7.0) ***
//   §6.9 page 171 : 0x60FB.4 = RstStart(0=off,1=on), 0x6098 = Homing method(0=off,1~37),
//                   0x6099 = Homing speeds(0.1 r/min), 0x6041 bit15 = 0:진행중 / 1:완료
//   §4.6 page 116 : Home 1/2(리밋 트리거)는 PP 모드에서만 유효. 드라이브가 리밋 입력
//                   (DI4/DI2)을 기본 원점으로 취급. 호밍 120초 초과 시 에러.
//                   RstMode 기본값 = 1 (Home 1, 음의 리밋)
//   실기 판독(2026-07-27): 전 노드 0x6098 = 1 → Home 1 확정. 조향축 0x6060 = 1(PP).
//
// *** 설계 결정 ***
//  (a) 구동축(node 1·2)은 대상이 아니다. 구동륜은 기계적 원점이 없고, 캡처에서도 Seer 가
//      조향 노드에만 호밍을 보냈다. TR_Nav 도 walk 모터는 호밍하지 않는다.
//  (b) **0x6098(method)을 쓰지 않는다.** Seer 도 쓰지 않고, 드라이브 저장값 1(Home 1)로
//      정상 동작하는 것을 실기 판독으로 확인했다. 특히 TR_Nav 처럼 마무리에 35 를 쓰면
//      Handbook §4.6 page 122 대로 RstMode 가 **0(호밍 꺼짐)으로 리셋**되는데, 우리 장비는
//      Seer 가 0x6098 을 절대 쓰지 않으므로 이후 Seer 호밍이 조용히 죽는다.
//  (c) 중단은 0x60FB.4 = 0 (Reset off) 으로 한다. 0x6040 servo-off 는 홀딩토크를 잃어
//      접지 상태에서 위험하므로 쓰지 않는다.
//  (d) 조향 0° 절대 counts 는 **차량별 상수**다. 아래 값은 본 차량 실측이며, 다른 차량에
//      올릴 때 반드시 재측정해야 한다.
extern uint16_t current_safety_mode;
#define SEER_HOME_REQ_SAFETY_MODE 30U   // = SAFETY_SEER_GATE (safety.h:57)

#define SEER_HOME_NODE_LO   3U       // 조향 노드 하한 (FrontSteer)
#define SEER_HOME_NODE_HI   4U       // 조향 노드 상한 (RearSteer)
#define SEER_HOME_NODE_CNT  2U
#define SEER_HOME_SPEED_DEF 2500U    // 0.1 r/min — Seer 실측값(Handbook 기본은 1000)
#define SEER_HOME_TIMEOUT_S 120U     // Handbook §4.6 page 116 의 호밍 타임아웃과 동일
#define SEER_HOME_POLL_DIV  2U       // 8Hz tick 기준 4Hz 로 피드백 폴

// 호밍 후 조향 0° 복귀 — 전부 Seer 실측값(위 t=49.03~49.14)
#define SEER_HOME_ZERO_N3   7882020  // node3(FrontSteer) 조향 0° 절대 counts
#define SEER_HOME_ZERO_N4   7859062  // node4(RearSteer)  조향 0° 절대 counts
#define SEER_HOME_PROF_VEL  30000U   // 0x6081
#define SEER_HOME_PROF_ACC  250U     // 0x6083
#define SEER_HOME_PROF_DEC  250U     // 0x6084
#define SEER_HOME_ZERO_TOL  57344    // 도달 판정 허용오차 = 1.0° (57344 counts/°)
#define SEER_HOME_ZERO_TMO_S 30U     // 0° 복귀 타임아웃(초). 실측 이동 소요 약 3초
#define SEER_HOME_CW_ENABLE 0x86U    // fault reset + enable (Seer 실측 관례)
#define SEER_HOME_CW_SETPOINT 0x3FU  // 신규 setpoint + 즉시적용 (Seer 실측 관례)

// 상태 — 호스트는 0xeb 로 읽는다
#define SEER_HOME_IDLE      0U
#define SEER_HOME_ENABLE    1U       // 0x6040 = 0x86
#define SEER_HOME_SET_SPEED 2U       // 0x6099 송신
#define SEER_HOME_START     3U       // 0x60FB.4 = 1 송신
#define SEER_HOME_WAIT      4U       // bit15 감시 (원점 탐색)
#define SEER_HOME_DONE      5U       // 조향 0° 복귀까지 완료
#define SEER_HOME_ERR_TIMEOUT 6U     // 원점 탐색 타임아웃(120s)
#define SEER_HOME_ERR_ABORT   7U     // 호스트 중단 또는 권한 상실
#define SEER_HOME_RESTORE   8U       // 0x6060/0x6081/0x6083/0x6084 재설정
#define SEER_HOME_GOZERO    9U       // 조향 0° 지령 송신
#define SEER_HOME_GOZERO_W  11U      // 조향 0° 도달 대기
#define SEER_HOME_ERR_GOZERO 10U     // 원점은 잡았으나 0° 복귀 실패 — 축이 리밋 근처에 있을 수 있음

uint8_t seer_home_state = SEER_HOME_IDLE;
uint16_t seer_home_speed = SEER_HOME_SPEED_DEF;
uint16_t seer_home_elapsed_s = 0U;   // 현 단계 경과(초)
uint8_t seer_home_tick_cnt = 0U;     // 8Hz 누산기
uint8_t seer_home_poll_cnt = 0U;
uint8_t seer_home_seen_active = 0U;  // bit0:node3, bit1:node4 — bit15==0(진행중)을 본 적 있음
uint8_t seer_home_done_mask = 0U;    // bit0:node3, bit1:node4 — bit15 0→1 전이 관측(원점 확정)
uint8_t seer_home_reached_mask = 0U; // bit0:node3, bit1:node4 — 조향 0° 도달

static int32_t seer_home_zero_target(uint8_t node) {
  return (node == SEER_HOME_NODE_LO) ? (int32_t)SEER_HOME_ZERO_N3 : (int32_t)SEER_HOME_ZERO_N4;
}

static void seer_send_bus2(uint32_t sndaddr, const uint8_t *d) {
  CANPacket_t p;
  p.rtr = 0U; p.returned = 0U; p.rejected = 0U; p.extended = 0U;
  p.bus = 2U;                        // bus2 = 모터 (PINMAP)
  p.addr = sndaddr;
  p.data_len_code = 8U;
  for (int i = 0; i < 8; i++) { p.data[i] = d[i]; }
  can_send(&p, 2U, true);
}

// SDO expedited write — size 1/2/4
static void seer_home_sdo_write(uint8_t node, uint16_t index, uint8_t sub,
                                uint32_t value, uint8_t size) {
  uint8_t d[8];
  uint8_t cmd;
  if (size == 1U) { cmd = 0x2FU; } else if (size == 2U) { cmd = 0x2BU; } else { cmd = 0x23U; }
  d[0] = cmd;
  d[1] = (uint8_t)(index & 0xFFU);
  d[2] = (uint8_t)((index >> 8) & 0xFFU);
  d[3] = sub;
  d[4] = (uint8_t)(value & 0xFFU);
  d[5] = (uint8_t)((value >> 8) & 0xFFU);
  d[6] = (uint8_t)((value >> 16) & 0xFFU);
  d[7] = (uint8_t)((value >> 24) & 0xFFU);
  seer_send_bus2((uint32_t)(0x600U + node), d);
}

static void seer_home_sdo_read(uint8_t node, uint16_t index, uint8_t sub) {
  uint8_t d[8];
  d[0] = 0x40U;
  d[1] = (uint8_t)(index & 0xFFU);
  d[2] = (uint8_t)((index >> 8) & 0xFFU);
  d[3] = sub;
  d[4] = 0U; d[5] = 0U; d[6] = 0U; d[7] = 0U;
  seer_send_bus2((uint32_t)(0x600U + node), d);
}

// 캐시에서 값을 꺼낸다. 캐시는 seer_cache_store_resp() 가 bus2 응답으로 갱신한다.
static bool seer_home_cached_sub(uint8_t node, uint16_t index, uint8_t sub, uint32_t *out) {
  for (int i = 0; i < SEER_CACHE_N; i++) {
    if ((seer_cache[i].valid != 0U) && (seer_cache[i].node == node) &&
        (seer_cache[i].index == index) && (seer_cache[i].sub == sub)) {
      *out = (uint32_t)seer_cache[i].data[4] |
             ((uint32_t)seer_cache[i].data[5] << 8) |
             ((uint32_t)seer_cache[i].data[6] << 16) |
             ((uint32_t)seer_cache[i].data[7] << 24);
      return true;
    }
  }
  return false;
}

static bool seer_home_cached(uint8_t node, uint16_t index, uint32_t *out) {
  return seer_home_cached_sub(node, index, 0U, out);
}

// 0x6000(Digital Input) 하위바이트. 펌웨어는 이 값으로 **분기하지 않고** 호스트에 그대로
// 돌려준다(0xeb) — 비트 매핑이 아직 1차 source 로 확정되지 않았기 때문이다.
// ⚠ 정정 (2026-07-27): 위 "비트 매핑이 아직 1차 source 로 확정되지 않았다"는 사유는 **무효**다.
//   sub 1 의 bit0 = ServoEnable, bit3 = −Limit 이 실기 캡처로 확정됐다
//   (Log/homing_capture_220350.jsonl: node3 t=47.0249 0x01→0x09 / t=49.4223 0x09→0x01,
//    node4 t=47.0254 / t=49.4227, 구동축 node1·2 는 420 폴 전량 0x01 무변화).
//   비분기(값을 그대로 호스트에 보고) 방침 자체는 유지한다 — 코드 변경 없음.
static uint8_t seer_home_digital_in(uint8_t node) {
  uint32_t v = 0U;
  // ⚠ 0x6000 은 **배열 오브젝트**다. sub 0 은 항목 수(=2)를 돌려주므로 실제 입력값은 sub 1.
  //   근거: 2026-07-27 실측 — sub 0 은 항상 0x02, sub 1 은 0x01(ServoEnable) / 0x09(+bit3 −Limit).
  //   TR_Nav 도 rpdo_mapped[0x6000][1] 로 sub 1 을 읽는다(can_open.hpp OnRpdoWrite 0x6000).
  return seer_home_cached_sub(node, 0x6000U, 0x01U, &v) ? (uint8_t)(v & 0xFFU) : 0xFFU;
}

static void seer_home_cancel_frames(void) {
  for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
    seer_home_sdo_write(n, 0x60FBU, 0x04U, 0U, 1U);   // RstStart = 0 (Reset off)
  }
}

static void seer_home_stage_reset(void) {
  seer_home_elapsed_s = 0U;
  seer_home_tick_cnt = 0U;
  seer_home_poll_cnt = 0U;
}

static bool seer_home_is_terminal(uint8_t st) {
  return (st == SEER_HOME_IDLE) || (st == SEER_HOME_DONE) ||
         (st == SEER_HOME_ERR_TIMEOUT) || (st == SEER_HOME_ERR_ABORT) ||
         (st == SEER_HOME_ERR_GOZERO);
}

// 호스트 명령 — usb_comms.h 0xea 에서 호출. start=true 개시, false 중단.
// 반환 false = 거부(사유는 0xeb 상태로 확인).
bool seer_homing_cmd(bool start, uint16_t speed) {
  if (!start) {
    if (!seer_home_is_terminal(seer_home_state)) {
      seer_home_cancel_frames();
      seer_home_state = SEER_HOME_ERR_ABORT;
    } else {
      seer_home_state = SEER_HOME_IDLE;
    }
    return true;
  }
  // 개시 인터록: PC 가 게이트를 잡고 있어야 한다. Seer 주도 중이면 Seer 의 호밍과 충돌한다.
  if (!pc_authority) { return false; }
  if (current_safety_mode != SEER_HOME_REQ_SAFETY_MODE) { return false; }
  if (!seer_home_is_terminal(seer_home_state)) { return false; }
  seer_home_speed = (speed == 0U) ? SEER_HOME_SPEED_DEF : speed;
  seer_home_stage_reset();
  seer_home_seen_active = 0U;
  seer_home_done_mask = 0U;
  seer_home_reached_mask = 0U;
  seer_home_state = SEER_HOME_ENABLE;
  return true;
}

// 8Hz tick — main.c tick_handler 에서 호출.
void seer_homing_tick(void) {
  if (seer_home_is_terminal(seer_home_state)) { return; }

  // 권한 상실 시 즉시 중단. heartbeat 상실은 main.c 가 pc_authority=false 로 떨어뜨리므로
  // 그 경로도 여기서 잡힌다(fail-safe 일원화).
  if ((!pc_authority) || (current_safety_mode != SEER_HOME_REQ_SAFETY_MODE)) {
    seer_home_cancel_frames();
    seer_home_state = SEER_HOME_ERR_ABORT;
    return;
  }

  switch (seer_home_state) {
    case SEER_HOME_ENABLE:
      for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
        seer_home_sdo_write(n, 0x6040U, 0U, (uint32_t)SEER_HOME_CW_ENABLE, 2U);
      }
      seer_home_state = SEER_HOME_SET_SPEED;
      break;

    case SEER_HOME_SET_SPEED:
      for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
        seer_home_sdo_write(n, 0x6099U, 0U, (uint32_t)seer_home_speed, 4U);
      }
      seer_home_state = SEER_HOME_START;
      break;

    case SEER_HOME_START:
      // 0x6098(method)은 쓰지 않는다 — 설계 결정 (b)
      for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
        seer_home_sdo_write(n, 0x60FBU, 0x04U, 1U, 1U);   // RstStart = 1
      }
      seer_home_stage_reset();
      seer_home_state = SEER_HOME_WAIT;
      break;

    case SEER_HOME_WAIT:
      seer_home_poll_cnt++;
      if (seer_home_poll_cnt >= SEER_HOME_POLL_DIV) {
        seer_home_poll_cnt = 0U;
        for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
          seer_home_sdo_read(n, 0x6041U, 0U);
          seer_home_sdo_read(n, 0x6000U, 0x01U);   // 리밋 상태(호스트 보고용)
        }
      }
      // bit15: 0=진행중 → 1=완료. 반드시 0 을 먼저 본 뒤의 1 만 완료로 인정한다
      // (개시 전 잔류 1 을 완료로 오인하는 것 방지)
      for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
        uint32_t sw = 0U;
        uint8_t bit = (uint8_t)(1U << (n - SEER_HOME_NODE_LO));
        if (seer_home_cached(n, 0x6041U, &sw)) {
          if ((sw & 0x8000U) == 0U) {
            seer_home_seen_active |= bit;
          } else if ((seer_home_seen_active & bit) != 0U) {
            seer_home_done_mask |= bit;
          } else {
            // 아직 진행중을 못 봤다 — 잔류값일 수 있으므로 완료로 세지 않는다
          }
        }
      }
      if (seer_home_done_mask == ((1U << SEER_HOME_NODE_CNT) - 1U)) {
        seer_home_stage_reset();
        seer_home_state = SEER_HOME_RESTORE;   // 원점 확정 — 이제 조향 0° 로 복귀한다
      } else {
        seer_home_tick_cnt++;
        if (seer_home_tick_cnt >= 8U) {          // 8 tick = 1초
          seer_home_tick_cnt = 0U;
          seer_home_elapsed_s++;
          if (seer_home_elapsed_s >= SEER_HOME_TIMEOUT_S) {
            seer_home_cancel_frames();
            seer_home_state = SEER_HOME_ERR_TIMEOUT;
          }
        }
      }
      break;

    case SEER_HOME_RESTORE:
      // 호밍 후 위치모드·프로파일 재설정 (Seer 실측 t=49.03~49.06 과 동일)
      for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
        seer_home_sdo_write(n, 0x6060U, 0U, 1U, 1U);                          // PP
        seer_home_sdo_write(n, 0x6081U, 0U, (uint32_t)SEER_HOME_PROF_VEL, 4U);
        seer_home_sdo_write(n, 0x6083U, 0U, (uint32_t)SEER_HOME_PROF_ACC, 4U);
        seer_home_sdo_write(n, 0x6084U, 0U, (uint32_t)SEER_HOME_PROF_DEC, 4U);
      }
      seer_home_state = SEER_HOME_GOZERO;
      break;

    case SEER_HOME_GOZERO:
      // 조향 0° 절대지령 (Seer 실측 t=49.14 과 동일). 원점은 경유지, 여기가 종착지다.
      for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
        seer_home_sdo_write(n, 0x607AU, 0U, (uint32_t)seer_home_zero_target(n), 4U);
        seer_home_sdo_write(n, 0x6040U, 0U, (uint32_t)SEER_HOME_CW_SETPOINT, 2U);
      }
      seer_home_stage_reset();
      seer_home_state = SEER_HOME_GOZERO_W;
      break;

    case SEER_HOME_GOZERO_W:
      seer_home_poll_cnt++;
      if (seer_home_poll_cnt >= SEER_HOME_POLL_DIV) {
        seer_home_poll_cnt = 0U;
        for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
          seer_home_sdo_read(n, 0x6064U, 0U);   // 실측위치
          seer_home_sdo_read(n, 0x6000U, 0x01U);   // 리밋 해제 확인(호스트 보고용)
        }
      }
      for (uint8_t n = SEER_HOME_NODE_LO; n <= SEER_HOME_NODE_HI; n++) {
        uint32_t raw = 0U;
        uint8_t bit = (uint8_t)(1U << (n - SEER_HOME_NODE_LO));
        if (seer_home_cached(n, 0x6064U, &raw)) {
          int32_t err = (int32_t)raw - seer_home_zero_target(n);
          if (err < 0) { err = -err; }
          if (err < (int32_t)SEER_HOME_ZERO_TOL) {
            seer_home_reached_mask |= bit;
          } else {
            // 아직 이동 중
          }
        }
      }
      if (seer_home_reached_mask == ((1U << SEER_HOME_NODE_CNT) - 1U)) {
        seer_home_state = SEER_HOME_DONE;
      } else {
        seer_home_tick_cnt++;
        if (seer_home_tick_cnt >= 8U) {
          seer_home_tick_cnt = 0U;
          seer_home_elapsed_s++;
          if (seer_home_elapsed_s >= SEER_HOME_ZERO_TMO_S) {
            // 원점은 잡혔으나 0° 복귀를 확인하지 못했다. 축이 리밋 근처에 남아 있을 수 있으므로
            // 호스트가 0xeb 의 0x6000·도달마스크를 보고 조치해야 한다.
            seer_home_state = SEER_HOME_ERR_GOZERO;
          }
        }
      }
      break;

    default:
      seer_home_state = SEER_HOME_ERR_ABORT;
      break;
  }
}

const safety_hooks seer_gate_hooks = {
  .init = seer_gate_init,
  .rx = default_rx_hook,
  .tx = seer_gate_tx_hook,
  .tx_lin = seer_gate_tx_lin_hook,
  .fwd = seer_gate_fwd_hook,
};
