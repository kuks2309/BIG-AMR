#!/usr/bin/env python3
"""SICK 안전 스캐너의 UDP 데이터 출력 채널 목적지를 설정한다 (쓰기 — 신중히 쓸 것).

⚠ **이 도구는 센서 설정을 바꾼다.** 읽기만 하려면 `read_output_channels.py` 를 쓴다.

왜 필요한가: 우리 ROS2 드라이버는 기동해야만 채널을 설정한다. 그런데 채널을 잘못 점유해
남의 수신자(Seer)를 끊어 놓은 상태에서는, 드라이버를 다시 띄우는 것만으로는 원복이 안 된다
(드라이버는 자기 채널만 건드리고, 원래 목적지를 모른다). 2026-08-08 에 다른 세션이 옛 런치
(channel 0)로 스택을 띄워 Seer 라이다를 끊은 사고가 실제로 났다.

동작: **활성 구성을 읽어 목적지(IP·포트)만 바꿔 되쓴다.** 데이터 블록·발행 주기·각도 범위는
원본 그대로 보존한다 — 그래서 "무엇이 바뀌는지"가 IP·포트 두 값으로 한정된다.

⚠ 이 설정은 **영구적이지 않다**: "This configuration is not permanent, i.e. the previously saved
configuration will be active again after restarting the device."
[Data output via UDP and TCP/IP, 8022708/1W29, §6.3.2.2, page 62]
즉 센서 전원을 재인가하면 Safety Designer 저장 구성으로 돌아간다.

1차 source (인용 페이지는 8022708/1W29/2026-05-26 기준):
  - §6.2.4.3 Calling up methods — Cmd='M', Mode='I', Data = index(UINT) + parameters, page 37
  - §6.3.2.2 Configuring the data output — 메서드 Index **176**, Table 73 입력 파라미터, page 62
  - §6.3.1.4.2 Active configuration — 변수 Index 178, Table 66, page 58

사용:
  # 조회만 (아무것도 쓰지 않음)
  python3 set_output_channel.py 192.168.192.100 --channel 1 --to 192.168.192.10:6060 --dry-run
  # 실제 적용
  python3 set_output_channel.py 192.168.192.100 --channel 1 --to 192.168.192.10:6060
"""
import argparse
import socket
import struct
import sys

from read_output_channels import (COLA2_PORT, IDX_ACTIVE, STRIDE_ACTIVE, VERSION_LEN,
                                  _fault, _frame, _read_frame, close_session, open_session,
                                  read_variable)

METHOD_CONFIGURE = 176          # §6.3.2.2, page 62
PARAM_LEN = 28                  # Table 73: offset 0..27


def _describe(block):
    """채널 블록 24바이트(변수 오프셋 4..27)를 사람이 읽을 수 있게."""
    ip = ".".join(str(b) for b in block[4:8][::-1])
    port, freq = struct.unpack("<HH", block[8:12])
    return "enabled=%d iface=%d → %s:%d (매 %d번째 스캔)" % (block[0], block[1], ip, port, freq)


def set_channel(host, channel, dest_ip, dest_port, enable=True, dry_run=False):
    sock = socket.socket()
    sock.settimeout(8)
    sock.connect((host, COLA2_PORT))
    sid = None
    try:
        sid = open_session(sock)
        blob = read_variable(sock, sid, 10, IDX_ACTIVE)
        body = blob[VERSION_LEN:]
        n = len(body) // STRIDE_ACTIVE
        if not (0 <= channel < n):
            raise RuntimeError("채널 %d 는 이 기체에 없다 (채널 수 %d)" % (channel, n))

        # 템플릿은 **현재 활성인 채널**에서 가져온다 — 비활성 채널은 데이터 블록이 비어 있어
        # 그대로 쓰면 아무 내용 없는 스트림이 만들어진다. 활성 채널이 없으면 대상 채널을 쓴다.
        src = channel
        for i in range(n):
            blk = body[i * STRIDE_ACTIVE:i * STRIDE_ACTIVE + 24]
            if blk[0]:
                src = i
                break
        tmpl = bytearray(body[src * STRIDE_ACTIVE:src * STRIDE_ACTIVE + 24])
        cur = body[channel * STRIDE_ACTIVE:channel * STRIDE_ACTIVE + 24]
        print("  채널 %d 현재: %s" % (channel, _describe(cur)))
        print("  템플릿(채널 %d): %s" % (src, _describe(tmpl)))

        tmpl[0] = 1 if enable else 0
        tmpl[4:8] = bytes(int(x) for x in dest_ip.split("."))[::-1]   # Little Endian
        struct.pack_into("<H", tmpl, 8, dest_port)
        print("  적용 예정: %s" % _describe(tmpl))
        if dry_run:
            print("  --dry-run — 쓰지 않고 종료")
            return

        # Table 73: channel(1) + Reserved(3) + [블록 24바이트]
        param = struct.pack("<B3x", channel) + bytes(tmpl)
        assert len(param) == PARAM_LEN, len(param)
        sock.sendall(_frame(sid, 11, b"M", b"I",
                            struct.pack("<H", METHOD_CONFIGURE) + param))
        # §6.2.2 "After a method invocation the sensor sends two answers: immediately a
        #         confirmation and later a result." → 'A'/'I' 가 나올 때까지 최대 2프레임 읽는다.
        for _ in range(2):
            _, _, cmd, mode, payload = _read_frame(sock)
            if cmd == b"F":
                raise RuntimeError("메서드 거부 — %s" % _fault(payload))
            if cmd == b"A" and mode == b"I":
                print("  ✅ 적용됨 (Cmd=A/Mode=I)")
                return
        print("  ⚠ 확인 응답을 못 받았다 — read_output_channels.py 로 결과를 직접 확인할 것")
    finally:
        if sid is not None:
            close_session(sock, sid)
        sock.close()


def main():
    ap = argparse.ArgumentParser(description="SICK 출력 채널 목적지 설정 (쓰기)")
    ap.add_argument("sensor", help="센서 IP")
    ap.add_argument("--channel", type=int, required=True, help="설정할 채널 번호 (0…3)")
    ap.add_argument("--to", required=True, metavar="IP:PORT", help="수신자 주소")
    ap.add_argument("--disable", action="store_true", help="채널을 끈다")
    ap.add_argument("--dry-run", action="store_true", help="바뀔 내용만 보이고 쓰지 않는다")
    a = ap.parse_args()
    ip, _, port = a.to.partition(":")
    print("센서 %s · 채널 %d" % (a.sensor, a.channel))
    set_channel(a.sensor, a.channel, ip, int(port), enable=not a.disable, dry_run=a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
