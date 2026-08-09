"""기동 전 가드 — 남이 쓰는 UDP 출력 채널을 빼앗으려 하면 런치를 중단시킨다.

## 왜 필요한가 (사고 2건에서 나옴)

이 드라이버는 기동할 때마다 CoLa 2 `changeSensorSettings()` 로 **센서 쪽 출력 채널의 목적지**를
덮어쓴다(`SickSafetyscanners.cpp:145`). 채널은 목적지를 하나만 기억하므로, 이미 누가 쓰는 채널을
지정하면 **그 수신자를 끊는다.** 끊긴 쪽(Seer)은 스스로 복구하지 못한다.

- 2026-08-07: 우리 런치가 채널 0 을 써서 Seer 라이다가 죽었다. 로봇 전원 재인가로 복구.
- 2026-08-08: 같은 사고 재발. 채널 1 로 고쳤지만 그 수정이 **한 세션 워크트리에만 있어**
  다른 세션이 옛 런치(채널 0)로 스택을 띄웠다.

두 번 다 **주석·문서로는 막히지 않았다.** 사람이 읽어야 작동하는 방지책은, 그 파일을 보지 않는
경로로 기동하면 무력하다. 그래서 기동 경로 자체에 기계 검사를 넣는다.

## 무엇을 검사하나

센서의 **저장 구성**(Safety Designer 로 저장, 재부팅 후에도 유효)을 읽어, 쓰려는 채널이 거기서
**활성**이면 남의 것으로 보고 `RuntimeError` 로 런치를 중단한다.

판정 근거를 저장 구성으로 잡은 이유: 활성 구성은 우리 런타임 변경이 섞여 있어, 우리가 이미
빼앗은 상태에서 "내 것"으로 보이는 자기충족 판정이 된다.

센서에 닿지 못하면 **통과시킨다** — 못 닿으면 설정을 바꿀 수도 없으므로 해를 끼칠 수 없고,
드라이버가 곧바로 자기 오류로 죽는다. 없는 위험 때문에 기동을 막지 않는다.

## 1차 source (8022708/1W29/2026-05-26 기준)

- §6.2.3.1 Setup of a session — Cmd='O'/Mode='X', data = Timeout(1) + ClientID, page 34~35
- §6.2.4   Read variable — Cmd='R'/Mode='I', index는 Little Endian, page 36
- §6.3.1.4.1 Saved configuration of the data output channel — 변수 Index **177**, Table 63, page 56
"""
import socket
import struct

COLA2_PORT = 2122
IDX_SAVED = 177
STRIDE = 24          # Table 63: 채널당 24바이트 (전체 오프셋 4..27)
VERSION_LEN = 4


def _recv(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise RuntimeError("연결이 끊겼다")
        buf += chunk
    return buf


def _frame(session_id, req_id, cmd, mode, data=b""):
    body = struct.pack("!BBIH", 0, 0, session_id, req_id) + cmd + mode + data
    return b"\x02\x02\x02\x02" + struct.pack("!I", len(body)) + body


def _read_frame(sock):
    head = _recv(sock, 8)
    if head[:4] != b"\x02\x02\x02\x02":
        raise RuntimeError("CoLa 2 STX 불일치")
    (length,) = struct.unpack("!I", head[4:])
    body = _recv(sock, length)
    session_id, _ = struct.unpack("!IH", body[2:8])
    return session_id, body[8:9], body[9:10], body[10:]


def saved_channels(sensor_ip, timeout=4.0):
    """저장 구성을 읽어 [(채널번호, 활성여부, "IP:PORT"), …] 반환. 닿지 못하면 None."""
    sock = socket.socket()
    sock.settimeout(timeout)
    try:
        sock.connect((sensor_ip, COLA2_PORT))
    except OSError:
        sock.close()
        return None
    try:
        # ⚠ ClientID 는 정확히 4바이트여야 한다 — 5바이트면 0x000E FLEX_OUT_OF_BOUNDS,
        #   생략하면 0x0008 BUFFER_UNDERFLOW 로 거부된다. [실측 2026-08-07]
        sock.sendall(_frame(0, 1, b"O", b"X", struct.pack("!B", 10) + b"\x00\x00\x00\x01"))
        sid, cmd, mode, _ = _read_frame(sock)
        if cmd != b"O" or mode != b"A":
            return None
        sock.sendall(_frame(sid, 2, b"R", b"I", struct.pack("<H", IDX_SAVED)))
        _, cmd, mode, payload = _read_frame(sock)
        if cmd != b"R" or mode != b"A":
            return None
        body = payload[2:][VERSION_LEN:]          # 인덱스 반향 2바이트 + 구조 버전 4바이트 제거
        out = []
        for i in range(len(body) // STRIDE):
            c = body[i * STRIDE:(i + 1) * STRIDE]
            ip = ".".join(str(b) for b in c[4:8][::-1])       # Little Endian
            (port,) = struct.unpack("<H", c[8:10])
            out.append((i, bool(c[0]), "%s:%d" % (ip, port)))
        try:
            sock.sendall(_frame(sid, 99, b"C", b"X"))
            _read_frame(sock)
        except (OSError, RuntimeError):
            pass
        return out
    except (OSError, RuntimeError, struct.error):
        return None
    finally:
        sock.close()


def assert_channel_free(sensor_ip, channel, label=""):
    """쓰려는 채널이 저장 구성에서 활성이면 RuntimeError. 조회 불가면 경고만 하고 통과."""
    tag = "[channel_guard%s]" % (" " + label if label else "")
    chans = saved_channels(sensor_ip)
    if chans is None:
        print("%s %s 저장 구성을 읽지 못했다 — 검사 생략(센서에 닿지 못하면 설정도 못 바꾼다)"
              % (tag, sensor_ip))
        return
    taken = [c for c in chans if c[1]]
    mine = [c for c in chans if c[0] == channel]
    if not mine:
        raise RuntimeError(
            "%s %s 에 채널 %d 가 없다. 이 기체의 채널: %s"
            % (tag, sensor_ip, channel, ", ".join(str(c[0]) for c in chans)))
    if mine[0][1]:
        free = [str(c[0]) for c in chans if not c[1]]
        raise RuntimeError(
            "%s %s 채널 %d 는 저장 구성에서 **이미 %s 에게 배정**돼 있다. "
            "이 채널을 쓰면 그 수신자(대개 Seer)의 라이다가 끊기고, 전원 재인가 또는 "
            "Tools/sick_channel_audit/set_output_channel.py 없이는 복구되지 않는다. "
            "비어 있는 채널: %s. 자세한 절차는 docs/lidar/sick_output_channel_setup.md §2."
            % (tag, sensor_ip, channel, mine[0][2], ", ".join(free) or "없음"))
    print("%s %s 채널 %d 사용 가능 (저장 구성 점유: %s)"
          % (tag, sensor_ip, channel,
             ", ".join("ch%d→%s" % (c[0], c[2]) for c in taken) or "없음"))
