#!/usr/bin/env python3
"""SICK 안전 스캐너의 UDP 데이터 출력 채널 구성을 읽는다 (읽기 전용).

왜 필요한가: 우리 ROS2 드라이버는 기동 시 `changeSensorSettings()` 로 **런타임** 채널 설정을
덮어쓴다. 그런데 그 설정은 영구적이지 않고, 센서에는 Safety Designer 로 저장한 **별도의 구성**이
따로 있다. 둘을 구분해 보지 않으면 "우리가 남의 채널을 뺏었는지" 를 알 수 없다.
2026-08-07 에 실제로 채널 0(Seer 용)을 빼앗아 Seer 라이다가 죽었고, 전원 재인가로만 복구됐다.

이 도구는 두 변수를 모두 읽어 나란히 보여준다 — **아무것도 쓰지 않는다.**

  Index 177  저장 구성(saved)  — Safety Designer 로 저장된 값. 재부팅 후 활성화된다.
  Index 178  활성 구성(active) — 지금 실제로 동작 중인 값. 런타임 변경이 반영돼 있다.

1차 source: [microScan3/outdoorScan3/nanoScan3 — Data output via UDP and TCP/IP,
8022708/1W29/2026-05-26](../../References/sick/nanoscan3/technical_information_data_output_udp_tcpip_en_im0083701.pdf)
  - §6.2.2.2 Layer 7.2 command layer (헤더 필드), page 33
  - §6.2.3.1 Setup of a session (Cmd='O'/Mode='X'), page 34~35
  - §6.2.3   Close session (Cmd='C'/Mode='X'), page 35
  - §6.3.1.4.1 Saved configuration, Table 63 (구조), page 56
  - §6.3.1.4.2 Active configuration, Table 66, page 58

사용:
  python3 read_output_channels.py 192.168.192.100 192.168.192.101
"""
import socket
import struct
import sys

COLA2_PORT = 2122          # CoLa 2 TCP 포트 (드라이버 기본값과 동일)
IDX_SAVED = 177
IDX_ACTIVE = 178

# 채널 구조 — 전체 오프셋 기준이며 채널 0 이 offset 4 에서 시작한다.
#   설정값 24바이트(두 변수 공통): oEnabled(4) eInterfaceType(5) Rsv(6..7)
#     tReceiverAddress(8..11) u16PortNumber(12..13) u16PublishingFreq(14..15)
#     AngleStart(16..19) AngleStop(20..23) tFeatures(24..25) Rsv(26..27)
#   ⚠ **두 변수의 채널 stride 가 다르다.** 저장(Table 63)은 설정값만이라 24바이트지만,
#     활성(Table 66)은 뒤에 파생값 24바이트가 더 붙어 **48바이트**다
#     (u16MultiplicationFactor(28) u16NumBeams(30) u16ScanTime(32) Rsv(34)
#      StartAngle(36..39) AngularScanBeamResolution(40..43) InterBeamPeriod(44..47) Rsv(48..51)).
#     stride 를 24 로 통일하면 활성 구성이 **채널 8개로 잘못 쪼개진다** — 실제로 그렇게 오독했다.
STRIDE_SAVED = 24          # Table 63, page 56~57
STRIDE_ACTIVE = 48         # Table 66, page 58~59
VERSION_LEN = 4            # cVersion, u8Major, u8Minor, u8Release

INTERFACE_TYPE = {0: "EFI-pro", 1: "Ethernet/IP", 3: "PROFINET", 4: "Non-secure Ethernet"}

FEATURE_BITS = ["Device status", "Configuration of the data output", "Measurement data",
                "Object detection", "Application data", "Local inputs and outputs"]

# Table 20 "Fault numbers", page 38. Cmd='F'/Mode='A' 응답의 데이터는 이 번호(UINT)다.
FAULTS = {
    0x0001: "METHODIN_ACCESSDENIED — 사용자 그룹 부족",
    0x0002: "METHODIN_UNKNOWNINDEX — 없는 메서드 인덱스",
    0x0003: "VARIABLE_UNKNOWNINDEX — 없는 변수 인덱스",
    0x0004: "LOCALCONDITIONFAILED — 값이 허용 범위 밖",
    0x0005: "INVALID_DATA — 변수에 부적합한 데이터",
    0x0006: "UNKNOWN_ERROR",
    0x0007: "BUFFER_OVERFLOW",
    0x0008: "BUFFER_UNDERFLOW — 데이터가 더 필요하다",
    0x0009: "ERROR_UNKNOWN_TYPE",
    0x000A: "VARIABLE_WRITE_ACCESS_DENIED",
    0x000B: "UNKNOWN_CMD_FOR_NAMESERVER",
    0x000C: "UNKNOWN_COLA_COMMAND",
    0x000D: "METHODIN_SERVER_BUSY",
    0x000E: "FLEX_OUT_OF_BOUNDS — 배열 길이가 틀렸다",
    0x000F: "EVENTREG_UNKNOWNINDEX",
    0x0010: "COLA_A_VALUE_OVERFLOW",
    0x0011: "COLA_A_INVALID_CHARACTER",
}


def _fault(payload):
    if len(payload) >= 2:
        (code,) = struct.unpack("<H", payload[:2])
        return "0x%04X %s" % (code, FAULTS.get(code, "미등록 코드"))
    return "코드 없음 (payload=%s)" % payload.hex()


def _recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise RuntimeError("연결이 끊겼다")
        buf += chunk
    return buf


def _frame(session_id, req_id, cmd, mode, data=b""):
    """CoLa 2 텔레그램 조립. 길이 필드는 그 뒤 전체 바이트 수다 (§6.2.2.2)."""
    body = struct.pack("!BBIH", 0, 0, session_id, req_id) + cmd + mode + data
    return b"\x02\x02\x02\x02" + struct.pack("!I", len(body)) + body


def _read_frame(sock):
    head = _recv_exact(sock, 8)
    if head[:4] != b"\x02\x02\x02\x02":
        raise RuntimeError("CoLa 2 STX 불일치: %s" % head[:4].hex())
    (length,) = struct.unpack("!I", head[4:])
    body = _recv_exact(sock, length)
    session_id, req_id = struct.unpack("!IH", body[2:8])
    return session_id, req_id, body[8:9], body[9:10], body[10:]


def open_session(sock, timeout_s=10, client_id=b"\x00\x00\x00\x01"):
    """§6.2.3.1 — SessionID=0, Cmd='O', Mode='X', data = Timeout(1) + ClientID.

    ⚠ ClientID 는 **정확히 4바이트**여야 한다. 문서는 "bytestream" 이라고만 적어 길이를 명시하지
    않지만, 실기(NANS3-CAAZ30AN1P02 FW R01.66)는 5바이트 ASCII 에 `0x000E FLEX_OUT_OF_BOUNDS`,
    아예 생략하면 `0x0008 BUFFER_UNDERFLOW` 로 거부했다. 4바이트에서만 열린다. [실측 2026-08-07]
    """
    sock.sendall(_frame(0, 1, b"O", b"X", struct.pack("!B", timeout_s) + client_id))
    sid, _, cmd, mode, payload = _read_frame(sock)
    if cmd == b"F":
        raise RuntimeError("세션 개설 거부 — %s" % _fault(payload))
    if cmd != b"O" or mode != b"A":
        raise RuntimeError("세션 개설 거부: cmd=%s mode=%s" % (cmd, mode))
    return sid


def close_session(sock, sid):
    try:
        sock.sendall(_frame(sid, 99, b"C", b"X"))
        _read_frame(sock)
    except (OSError, RuntimeError):
        pass       # 타임아웃으로도 정리된다 — 종료 실패는 치명적이지 않다


def read_variable(sock, sid, req_id, index):
    """§6.2.4 — Cmd='R', Mode='I', data = index (little endian, §6.2.2.2.1)."""
    sock.sendall(_frame(sid, req_id, b"R", b"I", struct.pack("<H", index)))
    _, _, cmd, mode, payload = _read_frame(sock)
    if cmd == b"F":
        raise RuntimeError("변수 %d 읽기 거부 — %s" % (index, _fault(payload)))
    if cmd != b"R" or mode != b"A":
        raise RuntimeError("변수 %d 읽기 실패: cmd=%s mode=%s" % (index, cmd, mode))
    (echoed,) = struct.unpack("<H", payload[:2])
    if echoed != index:
        raise RuntimeError("인덱스 반향 불일치: 요청 %d, 응답 %d" % (index, echoed))
    return payload[2:]


def parse_channels(blob, stride):
    """Table 63/66 구조 해석. 반환: (version, [채널 dict]).

    채널 수는 기체 변이형에 따라 다르다("The number of available data output channels depends
    on the device variant", page 9). 그래서 개수를 4로 고정하지 않고 실제 길이에서 구한다.
    stride 가 맞지 않으면 나머지 바이트가 남으므로 그것으로 자체 검증한다.
    """
    if len(blob) < VERSION_LEN:
        raise RuntimeError("응답이 너무 짧다: %d 바이트" % len(blob))
    version = "%d.%d.%d (valid=%s)" % (blob[1], blob[2], blob[3], blob[0] != 0)
    body = blob[VERSION_LEN:]
    if len(body) % stride:
        raise RuntimeError("채널 stride %d 로 나누어떨어지지 않는다 (%d 바이트, 나머지 %d) — "
                           "구조 버전이 바뀌었을 수 있다"
                           % (stride, len(body), len(body) % stride))
    out = []
    for i in range(len(body) // stride):
        c = body[i * stride:(i + 1) * stride]
        ip = ".".join(str(b) for b in c[4:8][::-1])      # tReceiverAddress 는 Little Endian
        (port,) = struct.unpack("<H", c[8:10])
        (freq,) = struct.unpack("<H", c[10:12])
        (feat,) = struct.unpack("<H", c[20:22])
        entry = {
            "channel": i,
            "enabled": bool(c[0]),
            "interface": INTERFACE_TYPE.get(c[1], "미상(%d)" % c[1]),
            "receiver": "%s:%d" % (ip, port),
            "publish_every_nth": freq,
            "features": [name for b, name in enumerate(FEATURE_BITS) if feat & (1 << b)],
            "derived": None,
        }
        if stride >= STRIDE_ACTIVE:                       # Table 66 의 "Used values"
            beams, scan_ms = struct.unpack("<HH", c[26:30])
            entry["derived"] = "빔 %d개 · 스캔 %d ms" % (beams, scan_ms)
        out.append(entry)
    return version, out


def audit(host):
    print("=" * 78)
    print("센서 %s" % host)
    sock = socket.socket()
    sock.settimeout(8)
    try:
        sock.connect((host, COLA2_PORT))
    except OSError as e:
        print("  접속 실패: %s" % e)
        return
    sid = None
    try:
        sid = open_session(sock)
        print("  세션 %d 개설" % sid)
        for label, index, stride in (("저장(saved, Safety Designer)", IDX_SAVED, STRIDE_SAVED),
                                     ("활성(active, 현재 동작)", IDX_ACTIVE, STRIDE_ACTIVE)):
            try:
                ver, chans = parse_channels(read_variable(sock, sid, index, index), stride)
            except RuntimeError as e:
                print("  [%s] 읽기 실패 — %s" % (label, e))
                continue
            print("\n  ── %s · Index %d · 구조 버전 %s ──" % (label, index, ver))
            for c in chans:
                mark = "●" if c["enabled"] else "○"
                print("    %s 채널 %d  %-21s  %-19s  매 %d번째 스캔  [%s]%s"
                      % (mark, c["channel"], c["receiver"], c["interface"],
                         c["publish_every_nth"], ", ".join(c["features"]) or "없음",
                         "  · " + c["derived"] if c["derived"] else ""))
    except (OSError, RuntimeError) as e:
        print("  오류: %s" % e)
    finally:
        if sid is not None:
            close_session(sock, sid)
        sock.close()


def scan(cidr24):
    """대역에서 CoLa 2 포트가 열린 호스트를 찾는다 — 타 기체 이설 시 센서 IP 를 모를 때 쓴다.

    기체마다 센서 주소가 다르므로 이 저장소의 값(.100/.101)을 그대로 가정하면 안 된다.
    """
    import concurrent.futures as cf
    base = cidr24.rstrip(".").rsplit(".", 1)[0] if cidr24.count(".") == 3 else cidr24.rstrip(".")

    def probe(i):
        ip = "%s.%d" % (base, i)
        s = socket.socket()
        s.settimeout(0.7)
        try:
            s.connect((ip, COLA2_PORT))
            return ip
        except OSError:
            return None
        finally:
            s.close()

    print("대역 %s.0/24 에서 CoLa 2(tcp/%d) 탐색 …" % (base, COLA2_PORT))
    with cf.ThreadPoolExecutor(max_workers=64) as ex:
        found = [ip for ip in ex.map(probe, range(1, 255)) if ip]
    print("발견 %d대: %s" % (len(found), ", ".join(found) if found else "없음"))
    return found


def main():
    args = sys.argv[1:]
    if args and args[0] == "--scan":
        hosts = scan(args[1] if len(args) > 1 else "192.168.192")
    else:
        hosts = args or ["192.168.192.100", "192.168.192.101"]
    for h in hosts:
        audit(h)
    print("=" * 78)
    print("● = 활성 채널. **저장(saved) 구성에서 활성인 채널은 다른 수신자(예: Seer)의 것**이므로")
    print("   우리 드라이버가 그 번호를 쓰면 안 된다. 저장 구성에서 ○ 인 가장 낮은 번호를 고른다.")
    print("   저장 구성의 채널 0 수신 주소 = 사고 시 원복에 쓸 값이니 함께 적어 둘 것.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
