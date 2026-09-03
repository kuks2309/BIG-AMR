# 2026-09-04 — `_read_text` 관대 예외에 TypeError 추가 (전원 게이트 존)

## 무엇을

`sysfs.py` `_read_text` 의 예외 목록 `(OSError, UnicodeDecodeError)` → `+ TypeError`.

## 왜

CV 클러스터가 꺼진 Orin 기체(orin-nx-ford-test, L4T R36.4.7)에서 cv0/cv1/cv2-thermal
의 `temp` 노드는 raw read 가 None 을 돌려주고, pathlib `read_text()` 의 codecs 단계가
`TypeError: can't concat NoneType to bytes` 를 낸다. 관대 목록에 없어 reader 가 죽었고
테스트 29건이 같은 경로로 실패했다 — 설계 불변식("모든 reader 는 노드 부재에 관대")의
구멍이라 기체 확장에서 드러났다.

## 검증

기준기(tegra) 226 PASS · orin-nx-ford-test 226 PASS(29건 실패 해소) — 양기체 실행.
