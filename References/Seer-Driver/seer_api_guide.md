# SEER Robokit API — 개발자 가이드 (실전 활용)

> 목적: 이 문서 하나로 **Seer(SRC) 로봇에 TCP/ModbusTCP API 로 붙어서 개발**을 시작할 수 있게 한다.
> 수집·검증: 2026-07-26 (KST, sess:e717f1dd) · 1차 source = **github.com/seer-robotics 공식 SDK + 공식 PDF `robotkit-netprotocol-l-1.2.1`** · 화면 판독 = Feishu wiki(guest)
> 등급: ✓ = 공식 원문(PDF/코드/화면) 직접 확인 / ⚠ = 버전차·미확정. 버전: PDF **v1.2.1**, Feishu 최신 **v1.4.2**(차이는 §9).

---

## 0. 문서 맵 (어디에 무엇이 있나)

| 파일 | 내용 | 언제 본다 |
|---|---|---|
| **seer_api_guide.md** (이 문서) | 실전 개발 진입점: 프로토콜·클라이언트·레시피 | 개발 시작 시 |
| [robokit_tcp_api.md](robokit_tcp_api.md) | TCP/IP API 정본: 포트·헤더·**전체 API 편号 맵** | API 번호/필드 조회 |
| [robokit_tcp_api_laser.md](robokit_tcp_api_laser.md) | 레이저(LiDAR) 포인트클라우드 API 1009 상세 | 라이다 데이터 pull |
| [can_timing_motor_controller.md](can_timing_motor_controller.md) | 통신/모터 **에러·알람** 변수 (52xxx/54xxx, 레지스터) | 고장 감시 |
| [sources.md](sources.md) | 전체 인덱스·출처·미확정 사항 | 근거 추적 |
| `github_sdk/` | **원본**: 공식 PDF(+추출 txt), Python 프로토콜/데모, C++ 헤더 | 원문 대조 |

---

## 1. 5분 개념 요약

- **역할**: 로봇 = **서버**, 이 PC = **클라이언트**. 로봇은 절대 능동 송신 안 함(Push API 19301 예외).
- **방식**: **TCP 1문1답**(Q&A). 한 연결에서 이전 응답을 받기 전 다음 요청 금지.
- **포트 = 기능 카테고리**. 카테고리별 독립 포트(아래 §2).
- **메시지 = 16바이트 헤더 + JSON**. 응답 편号 = 요청 편号 **+10000**.
- **요청 간격 ≥100~200ms** 권장(과빈번 시 로봇이 연결 정리) → 실효 폴링 ~5–10Hz.

---

## 2. 포트 맵 ✓

| 카테고리 | 상수 | 포트 | 동시연결(v1.2.1 / v1.4.2) | 용도 |
|---|---|---|---|---|
| Robot Status | `API_PORT_STATE` | **19204** | 10 / 10 | 조회(위치·속도·배터리·IO·알람·레이저…) |
| Robot Control | `API_PORT_CTRL` | **19205** | 1 / 5 | 즉시 제어(정지·재측위·개루프 운동) |
| Robot Task/Nav | `API_PORT_TASK` | **19206** | 1 / 5 | 내비게이션·작업(gotarget·평동·회전) |
| Robot Config | `API_PORT_CONFIG` | **19207** | 1 / 5 | 파라미터 설정/저장 |
| Robot Kernel | `API_PORT_KERNEL` | 19208 | — | 종료·재시작·펌웨어 리셋 |
| Other | `API_PORT_OTHER` | **19210** | 1 / 5 | DO 출력·스피커 |
| (daemon) | `API_PORT_ROBOD` | 19200 | — | 코어 프로세스 |
| **Push** | — | **19301** | — / 10 | 로봇 능동 push(구독) |

> ⚠ v1.2.1 은 Status 외 포트가 **동시연결 1**(선점 시 타 연결 거부). 여러 클라이언트가 붙는다면 v1.4.2 펌웨어 필요.

---

## 3. 메시지 프로토콜 (16B 헤더 + JSON) ✓

```c
struct ProtocolHeader {        // 16 byte, big-endian(network order)
    uint8_t  m_sync;           // [0]   = 0x5A (고정)
    uint8_t  m_version;        // [1]   = 0x01
    uint16_t m_number;         // [2-3] seq(0~65535). 응답은 같은 seq 반향
    uint32_t m_length;         // [4-7] JSON 바이트 길이(무파라미터=0)
    uint16_t m_type;           // [8-9] API 편号(요청 ID)
    uint8_t  m_reserved[6];    // [10-15] 0x00 채움(생략 불가)
};                             // 이어서 m_length 만큼 JSON(ascii)
```
규칙: 응답 편号=요청+10000 · 헤더 파싱 실패→로봇이 연결 끊음(무응답) · 엉뚱한 포트로 보내면 `60000` 응답.

---

## 4. 재사용 클라이언트 (복붙용) ✓ 공식 packMsg/unpackHead 기반

```python
import json, socket, struct, itertools

# 포트 상수 (netprotocol/rbkNetProtoEnums.py 원본)
API_PORT_STATE, API_PORT_CTRL, API_PORT_TASK = 19204, 19205, 19206
API_PORT_CONFIG, API_PORT_OTHER, API_PORT_PUSH = 19207, 19210, 19301
_HEAD_FMT = '!BBHLH6s'
_RSV = b'\x00\x00\x00\x00\x00\x00'

class SeerClient:
    """Seer Robokit NetProtocol TCP 클라이언트 (1문1답)."""
    def __init__(self, ip, port, timeout=5.0):
        self.ip, self.port, self.timeout = ip, port, timeout
        self._seq = itertools.cycle(range(1, 65536))
        self.so = None

    def connect(self):
        self.so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.so.settimeout(self.timeout)
        self.so.connect((self.ip, self.port))
        return self

    @staticmethod
    def _pack(seq, api, msg):
        body = b'' if not msg else json.dumps(msg).encode('ascii')
        return struct.pack(_HEAD_FMT, 0x5A, 1, seq, len(body), api, _RSV) + body

    def _recv_exact(self, n):
        buf = b''
        while len(buf) < n:
            chunk = self.so.recv(n - len(buf))
            if not chunk:
                raise ConnectionError('robot closed connection (헤더 불일치 가능)')
            buf += chunk
        return buf

    def request(self, api, msg=None):
        """api 요청 → dict 응답 반환. 응답 편号=api+10000."""
        seq = next(self._seq)
        self.so.sendall(self._pack(seq, api, msg or {}))
        head = self._recv_exact(16)
        _, _, r_seq, jlen, r_type, _ = struct.unpack(_HEAD_FMT, head)
        body = self._recv_exact(jlen) if jlen else b'{}'
        return json.loads(body.decode('utf-8', 'replace'))

    def close(self):
        if self.so: self.so.close(); self.so = None
    def __enter__(self): return self.connect()
    def __exit__(self, *a): self.close()

# 사용 예: 위치 조회
with SeerClient('192.168.44.82', API_PORT_STATE) as c:
    print(c.request(1004))          # robot_status_loc_req → {"x":..,"y":..,"angle":..}
```
> ⚠ 개선점(원본 데모 대비): `sendall`/`_recv_exact` 로 부분 수신·부분 송신 처리, seq 자동 증가. 원본 데모는 단순 `recv(1024)` 라 큰 응답(레이저 등)에서 잘릴 수 있음 → 반드시 헤더의 `m_length` 만큼 정확히 읽을 것.

---

## 5. 자주 쓰는 API 레시피 ✓ (편号·포트·JSON은 PDF/데모 확인)

| # | 하고 싶은 것 | 포트 | API | 요청 JSON | 응답 핵심 |
|---|---|---|---|---|---|
| 1 | 로봇 정보 | STATE 19204 | `1000` | `{}` | version, model 등 |
| 2 | **위치** | STATE | `1004` | `{}` | `x,y,angle` |
| 3 | **속도** | STATE | `1005` | `{}` | `vx,vy,w` |
| 4 | 배터리 | STATE | `1007` | `{}` | 배터리 상태 |
| 5 | IO(DI/DO) | STATE | `1013` | `{}` | DI/DO 배열 |
| 6 | 작업 상태 | STATE | `1020` | `{}` | task_status/사이트/경로 |
| 7 | **알람** | STATE | `1050` | `{}` | `fatals/errors/warnings`(§7) |
| 8 | 레이저 포인트클라우드 | STATE | `1009` | `{}`(또는 `{"step":N}`) | `lasers[].beams[]` ([[robokit_tcp_api_laser]]) |
| 9 | **배치 조회** | STATE | `1100` | `{}` | 1002~1050 대부분 한 번에 |
| 10 | 파라미터 조회 | STATE | `1400` | `{"plugin":"MoveFactory","param":"MaxAcc"}` | 플러그인별 값 |
| 11 | **개루프 운동** | CTRL 19205 | `2010` | `{"vx":0.1,"vy":0,"w":0}` | 즉시 반환(manual 모드만 유효) |
| 12 | 정지 | CTRL | `2000` | `{}` | — |
| 13 | 재측위 | CTRL | `2002` | `{"x":10.0,"y":3.0,"angle":0}` | — |
| 14 | 측위 확정 | CTRL | `2003` | `{}` | (init·loadmap·reloc 조건 충족 시) |
| 15 | **고정경로 내비** | TASK 19206 | `3051` | `{"id":"LM1"}` | 사이트 LM1 로 이동 |
| 16 | 작업 취소 | TASK | `3003` | `{}` | — |
| 17 | 파라미터 설정+저장 | CONFIG 19207 | `4002` | `{"MoveFactory":{"MaxAcc":1.0}}` | — |
| 18 | **DO 출력** | OTHER 19210 | `6001` | `{"id":15,"status":false}` | — |

```python
# 레시피 조합 예: manual 모드에서 전진 → 정지 (제어는 19205)
with SeerClient('192.168.44.82', API_PORT_CTRL) as c:
    c.request(2010, {"vx":0.1, "vy":0.0, "w":0.0})   # 0.1 m/s 전진
    # ... 이동 ...
    c.request(2000)                                   # 정지

# 스테이션 LM1 로 내비게이션 (작업은 19206)
with SeerClient('192.168.44.82', API_PORT_TASK) as c:
    c.request(3051, {"id":"LM1"})
```
> ⚠ 제어(2xxx)는 **manual 모드**에서만 유효(로봇 기동 시 기본 manual). 자동 모드 전환은 측위 확정(2003) 후 config 4000. 전체 필드는 [robokit_tcp_api.md](robokit_tcp_api.md) §4 + 원본 PDF 참조.

---

## 6. Push API (구독, 폴링 대안) ⚠

- 포트 **19301**, 동시 10 연결(v1.4.2). 로봇이 설정된 항목을 능동 push → 폴링 부담↓.
- 레이저·상태 등을 push 로 받을 수 있으나 **구독 항목 설정 방법은 미열람(⚠)**. 필요 시 Feishu "Robot Push API" 페이지 추가 판독.

---

## 7. 에러·알람 처리 ✓ (상세 [[can_timing_motor_controller]])

`1050` 응답 구조:
```json
{ "fatals":[{"50000":1497698400}],
  "errors":[{"52111":1497698402},{"52118":1497698404}],  // key=알람코드, value=발생시각(epoch@UTC+8)
  "warnings":[{"54003":1497698405}], "ret_code":0, "err_msg":"" }
```
통신/모터 핵심 코드: **52111**(드라이버 연결=CAN 링크), **52116~52118**(컨트롤러 네트워크/링크/서브시스템 단절), **52130~52135**(모터 과전압/과전류/과열/저전압), **54001**(배터리 통신), **54003/54004**(모터 과속/급정지). 전체표는 [can_timing_motor_controller.md](can_timing_motor_controller.md) §2.

```python
def poll_alarms(ip):
    with SeerClient(ip, API_PORT_STATE) as c:
        a = c.request(1050)
        for lvl in ('fatals','errors','warnings'):
            for item in a.get(lvl, []):
                for code, ts in item.items():
                    yield lvl, int(code), ts
```

---

## 8. ModbusTCP 대안 (PLC 연동) ✓

TCP/IP API 대신 ModbusTCP 로도 상태·에러코드 조회 가능. **주소는 문서 00001부터 → 실제 요청 시 −1 오프셋, float32=2레지스터**.

| 값 | 종류 | 주소(문서) |
|---|---|---|
| X/Y/angle | Input Reg float32 | 00001~00006 |
| Fatal/Error/Warning 코드 | Input Reg uint16 | 00031 / 00032 / 00033 |
| Error 코드 집합(6개) | Input Reg uint16 | 00120~00125 |
| 컨트롤러 온도/전압 | Input Reg float32 | 00021~00022 / 00025~00026 |
| Fatal/Error/Warning 유무 | Discrete Input bit | 00008 / 00009 / 00010 |
| 급정지 여부 | Discrete Input bit | 00004 |

---

## 9. 개발 체크리스트 & 함정

- [ ] **로봇 IP 확정**: 본 프로젝트 SRC 후보 `192.168.44.82`(무선 전용, [[biguamr-seer-network-access]]) — eth0 에 44대역 붙이지 말 것. 데모 IP(192.168.4.x/192.168.192.5)는 예시.
- [ ] **펌웨어 버전 확인**: v1.2.1 ↔ v1.4.2 로 포트 동시연결수·신규 API·필드가 다름. 실장비에서 `1000`(info)으로 버전 확인.
- [ ] **응답은 항상 헤더(16B)의 `m_length` 만큼 정확히 read** — `recv(1024)` 로 큰 응답 자르지 말 것.
- [ ] **요청 간격 ≥100~200ms**, 한 연결 1문1답 준수.
- [ ] **제어는 manual 모드에서만** 유효. 자동 내비는 측위 확정 필요.
- [ ] 카테고리↔포트 정확히 매칭(엉뚱한 포트=`60000` 에러).
- [ ] 다중 클라이언트면 Status(19204, 10연결) 활용, 제어계열은 연결 점유 주의.

---

## 10. 미확정 (⚠ 추후)

- ⚠ **raw CAN 설정**(baud/Node-ID/heartbeat/PDO/error-counter): 외부 API 미노출(RoboShop 내부). Seer↔Tongyi 실버스 CAN 캡처 필요. 하류 Tongyi=CANopen CiA301/402 ✓ ([[biguamr-motor-control-port]]).
- ⚠ Push API(19301) 구독 항목 설정법 미열람.
- ⚠ 일부 엔드포인트 상세 필드(전체 응답 스키마)는 PDF 원문(`github_sdk/robotkit-netprotocol-l-1.2.1.txt`) 대조 필요.
- ⚠ 참고 SDK: `github.com/seer-robotics/Robokit_TCP_API_py`(Python), `SeerTCPTest`(C++/Qt), `Robokit-Modbus`.
