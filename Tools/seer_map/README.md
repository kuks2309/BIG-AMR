# seer_map — Seer 맵 내려받기·그림으로 보기

Seer 컨트롤러에서 **현재 로드된 `.smap` 맵을 내려받고**, 그것을 인쇄·공유용 평면도 이미지로
렌더한다. 비-ROS2 독립 도구라 저장소 규약대로 `Tools/` 에 둔다(`python3` 즉시 실행, colcon 불요).

## 쓰는 법

```bash
# 1) 현재 로드된 맵 내려받기 (읽기 전용 조회 — 로봇에 쓰기 없음)
python3 Tools/seer_map/download_map.py map/
#    다른 기체: SEER_IP=192.168.x.y python3 Tools/seer_map/download_map.py map/

# 2) 평면도 이미지(PNG + JPG) 렌더
python3 Tools/seer_map/render_smap.py map/<맵>.smap map/<출력이름>
#    로봇 자세를 함께 그리려면 3번째 인자로 pose JSON
python3 Tools/seer_map/render_smap.py map/x.smap map/x '{"x":-12.2,"y":2.3,"angle":-3.11,"confidence":0.84}'
```

`download_map.py` 는 로봇이 보고한 `current_map_md5` 와 **받은 바이트의 md5 를 대조**해 무결성을
검증하고, 불일치면 종료코드 1 을 낸다.

## 프로토콜 근거

Robokit NetProtocol — 16바이트 헤더(`0x5A`, ver, seq, len, type, rsv6) + JSON 본문.

| 요청 | 포트 | 하는 일 |
| --- | --- | --- |
| `1300 robot_status_map_req` | 19204 | `current_map` · `current_map_md5` · `maps[]` |
| `4011 robot_config_downloadmap_req` | 19207 | 데이터부가 `.smap` JSON 원문 |
| `1004 robot_status_loc_req` | 19204 | 자세(x·y·angle·confidence) — 렌더 인자용 |

`4011` 은 저장소 동봉 PDF(`robotkit-netprotocol-l-1.2.1`)에 **없다**(그 판의 config API 는 4000·
4100·4101·4102·4300 뿐). v1.4 계열 문서에만 있으며 요청/응답 포맷 정본은
`kuks2309/T-Robot_seer_gui` 의 `references/seer/robokit-api/robot-configuration-api/019-download-maps-from-robots.md` 다.

## 함수표

| # | 함수 | 입력 | 출력 | 기능 | 위치 |
| --- | --- | --- | --- | --- | --- |
| 1 | `_recvn` | `sock`, `n` | `bytes` | 정확히 n 바이트 수신(부분 수신 루프) | download_map.py:23 |
| 2 | `request` | `port`, `req_type`, `payload`, `timeout` | `(resp_type, body)` | 헤더 조립·송신·응답 수신 | download_map.py:33 |
| 3 | `main` | argv[1]=출력디렉터리 | 종료코드 | 현재 맵 조회 → 다운로드 → md5 대조 → 저장·요약 출력 | download_map.py:48 |

`render_smap.py` 는 **함수 정의가 없는 직선 스크립트**다(로드 → 좌표 추출 → 레이어별 플롯 →
저장). 재사용할 부분이 생기면 그때 함수로 분리한다.

**전역 변수 / 모듈 상수**: 가변 전역 없음. 상수는 `IP`(`SEER_IP` 로 덮어씀)·`PORT_STATE`·
`PORT_CFG`·`REQ_*` 4종(download_map.py:18-20)과 렌더 색상 상수 `INK`/`OBST`/`RSSI`/`NAMED`/
`ROBOT`/`GRID`(render_smap.py:44).

## 의존성

| Tier | 대상 | 부재 시 동작 |
| --- | --- | --- |
| 런타임 필수 | Python 3 표준 라이브러리만 (`socket`·`struct`·`json`·`hashlib`) | — `download_map.py` 는 외부 의존성 0 |
| 런타임 필수 | `matplotlib` (렌더 전용) | `render_smap.py` 만 import 실패. 다운로드는 무관 |
| 런타임 선택 | Noto Sans CJK (`/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`) | 없으면 기본 폰트로 폴백 — 한글 라벨이 깨질 수 있다 |
| 런타임 필수 | Seer 컨트롤러 도달성(무선) | 소켓 연결 실패로 예외 |

## 주의

- **맵 파일·렌더 이미지는 저장소에 커밋하지 않는다**(용량). 필요할 때 위 명령으로 다시 만든다.
  단, 맵은 현장에서 재구축되면 같은 이름으로 내용이 바뀌므로(2026-08-06 실제 발생), 보존이
  필요하면 **날짜·md5 를 파일명에 붙여** 따로 남긴다 — 덮어쓰면 그 판은 복구할 수 없다.
- 조회는 전부 읽기 전용이다. 이 도구는 로봇에 아무것도 쓰지 않는다.
- `19207`(config)은 프로토콜 v1.2.1 기준 **동시연결 1** 이다. RoboShop 이 붙어 있으면 거부될 수 있다.
