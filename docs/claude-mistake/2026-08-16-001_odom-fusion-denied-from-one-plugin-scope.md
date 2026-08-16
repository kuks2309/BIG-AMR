---
id: 2026-08-16-001
type: mistake
category: context-missing
status: closed
reflected_assets:
  - docs/comparison/seer-odom-production_vs_big-amr_2026-08-07.md#1-파이프라인-
  - docs/comparison/seer-libmcloc-odom_vs_mcl2d-port_2026-07-31.md
  - Tools/seer_re/docs/legacy_runtime_wiring.md
  - docs/debt/registry.md
---

# 2026-08-16 14:40 (KST) — 플러그인 하나의 구독 목록으로 시스템 전체의 융합 부재를 단정

## 무엇을 했는가

사용자가 「seer legacy odom 은 엔코더 값만으로 구하나요?」라고 물었을 때
`libOdoCalculator.so` 를 조사해 다음을 확인하고 답했다.

- 모터 피드백(`Message_MotorInfo` 의 `encoder` → `dpos`/`v_enc`)만으로 자세를 만든다
- `OdoCalculator` 가 구독하는 것은 `NavSpeed`·`Controller`·`MotorInfos` **셋뿐**이다

여기까지는 실측이었다. 그런데 결론을 이렇게 적었다 —
**「외부 센서: 없음. IMU·레이저·GPS 융합 경로 없음」**, 그리고
**「위치추정 결과를 오도에 되먹여 리셋하는 구조가 아니다 ⇒ 오도 = 짧은 구간 이동량 센서로 격하」**.

## 무엇이 잘못이었나

**조사 범위는 플러그인 1개였는데 결론은 시스템 전체로 적었다.**

배포의 실제 배선은 `rbk/rbk.plugin`(로드 목록 + 토픽 구독 표)에 있고, 그 파일을 조사하지 않았다.
실제 경로는 다음과 같다:

```
DSPChassis ──MotorInfos──→ OdoCalculator ──Message_Odometer──→ RobotPosEKF ──Message_Odometer──→ MCLoc
DSPChassis ──IMU───────────────────────────────────────────→ RobotPosEKF
```

- `MCLoc` 은 `OdoCalculator` 의 오도를 **직접 받지 않는다.** `RobotPosEKF` 가 발행한 것을 받는다.
- `libRobotPosEKF.so` 는 `estimation::OdomEstimation` 클래스를 갖는다 —
  `addOdoMeasurement(Message_Odometer)` · `addImuMeasurement(Message_IMU)` · `update()` ·
  `getFilterOdometer(Message_Odometer&)`. ROS `robot_pose_ekf` 계열의 오도-IMU 융합기다.
- 배포 파라미터 `RobotPosEKF.UseIMU = 1` — **이 기체에서 융합이 켜져 있다.**

따라서 「위치추정이 소비하는 오도」는 **휠 오도가 아니라 휠 오도 + IMU 융합 결과**다.
「융합 경로 없음」은 사실이 아니었고, 드리프트 서술도 한 겹이 빠진 그림이었다.

## 사용자 지적

> 「⇒ 위치추정 결과를 오도에 되먹여 리셋하는 구조가 아닙니다 … <- seer legacy도 마찬가지?」
> 이어서 「**실제 레거시 동작은 확인해야 함**」

되묻지 않았으면 그대로 남았을 서술이다.

## 원인 분석

`context-missing`. 필요한 자료가 **같은 드라이브에 평문 JSON 으로 있었다**(`rbk/rbk.plugin`, 88줄).
심볼·디스어셈블로 파고드는 동안 **"무엇이 무엇을 구독하는가"를 선언한 배포 파일을 후보에 넣지 않았다.**

부재 주장의 근거를 좁게 잡은 것도 겹쳤다 — `OdoCalculator` 의 `setSubscriberCallBack` 목록은
「그 플러그인이 무엇을 받는가」만 말하고 「그 플러그인의 출력이 어디를 거쳐 소비자에게 가는가」는
말하지 않는다. 두 질문을 같은 것으로 취급했다.

이 저장소의 메타 패턴 「**「없다」의 근거 범위를 넘겨 일반화**」의 반복이다
(2026-08-03-002 · 2026-08-05-001 · 2026-08-06-002 · 2026-08-07-002 에 이어 다섯 번째).
앞선 네 건이 「문서에 없으니 없다」·「캡처에 없으니 없다」였다면 이번은 「한 모듈이 안 받으니 없다」다.

## 재발 방지

지식 보강 — **레거시 런타임 배선을 확정 자산으로 만들었다.**
`Tools/seer_re/docs/legacy_runtime_wiring.md` 에 `rbk.plugin` 에서 뽑은
플러그인 로드 순서와 토픽 pub→sub 표를 그대로 옮기고, 오도·측위 경로를 그림으로 고정했다.
앞으로 「원본에서 X 가 Y 를 받는가」는 심볼이 아니라 **이 표를 먼저** 본다.

두 대조 문서의 파이프라인 그림을 정정했다(`OdoCalculator → MCLoc` → `OdoCalculator → RobotPosEKF → MCLoc`).
`RobotPosEKF` 내부 동작은 미조사이므로 **debt-107** 로 등록했다 — 이번 정정은 「융합이 존재하고
켜져 있다」까지이고, 융합식·공분산·IMU 축 정렬은 아직 아무것도 확인하지 않았다.
