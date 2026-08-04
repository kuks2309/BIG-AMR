# Orbbec Gemini E / E Lite vs Astra Pro 성능 비교

> 작성일 2026-06-24 (KST) · 작성자 Claude
> 외부 참조 처리 규칙([handling.md](../claude_guideline/external_reference/handling.md)) 준수 — 모든 spec 주장에 검증 등급(✓/ⓦ/⚠) 부착.

## 검증 등급 범례

| 표기 | 의미 |
| --- | --- |
| ✓ | 1차 source(데이터시트 PDF) 직접 확인 |
| ⓦ | 제3자 문서가 벤더 spec 을 인용 — 벤더 원본 미대조 |
| ⚠ | 추정·출처 간 불일치, 확인 필요 |

## 출처 (Sources)

> **⚠ 2026-07-27 근거 감사 — 인용된 1차 source(PDF·텍스트 추출본)가 본 저장소에 존재하지 않는다.**
> 확인 명령/결과 (저장소 루트 `/home/nvidia/Project/Ford-CATL-AMR/Big-AMR`):
> - `ls *.pdf` → No such file (루트에 `Gemini E&E Lite Datasheet V1.0 - En.pdf` 없음)
> - `ls references` → No such file or directory (존재하는 것은 대문자 `References/` 이며 하위는 `motor_configuration`, `Seer-Driver`, `Tongyi-Motor-Controller` 뿐 — `references/orbbec/**` 없음)
>   - **(2026-08-04 후기)** 그 뒤 소문자 `references/`(seer/libMCLoc)가 별도로 생겨 두 폴더가 공존했고, 2026-08-04 `References/` 로 병합했다. 현재 하위는 `motor_configuration`, `Seer-Driver`, `Tongyi-Motor-Controller`, `seer` 4개이며 **`orbbec/**` 부재는 그대로**다. 이 대소문자 분기가 위 명령이 실패한 원인이므로, 이후 조회는 `ls References` 또는 `find . -maxdepth 1 -iname 'reference*'` 로 한다(external_reference §1·§14 #7).
> - `find /home/nvidia/Project -iname "*Gemini*.pdf" -o -iname "*astra*.pdf"` → 0건
> - `git ls-files | grep -i references/orbbec` → 0건
>
> **따라서 아래 ✓ 등급(= `:10` 정의상 "1차 source 데이터시트 PDF 직접 확인") 항목들은 현 저장소에서 재대조가 불가능하다.
> 원본 PDF 를 재수집해 대조하기 전까지 ✓ 는 신뢰할 수 없으며 사실상 ⓦ/⚠ 로 취급할 것.**
> 수치 자체는 그대로 둔다(값 변경 아님 — 등급 신뢰만 낮춤).

- **Gemini E / E Lite**: [Gemini E&E Lite Datasheet V1.0 - En, page 4-7](../../Gemini%20E&E%20Lite%20Datasheet%20V1.0%20-%20En.pdf) — Orbbec 공식 datasheet (저장소 루트 보관, 텍스트 추출본 `References/orbbec/gemini-e-lite/`) **(파일 미보관 — 2026-07-27 확인: 루트 PDF·참조 폴더 모두 부재)**
- **Astra Pro (헤드라인)**: [Orbbec Astra Overview, page 3](../../References/orbbec/astra-pro/Orbbec_Astra_Overview.pdf) — Orbbec 공식 family overview **(파일 미보관 — 2026-07-27 확인: `ls references` → No such file, `find … -iname "*astra*.pdf"` → 0건. 이 PDF 가 Astra Pro ✓ 등급의 유일한 "공식 1차" 근거인데(`:24` "단독 마케팅 datasheet PDF 는 호스팅되지 않는다", `:83` "공식 단독 datasheet 미수집") 저장소에서 확인되지 않는다 → 재수집 전까지 이 출처 기반 ✓ 는 ⚠ 로 낮출 것)**
- **Astra Pro (상세 spec)**: ZMD Depth Sensors — Orbbec Astra (Pro), Media Research Lab, Rev 0.1 Draft 2016-09-24 (Orbbec spec 인용 제3자 문서), https://mrl.cs.vsb.cz/people/fabian/zmd/pr10.pdf (accessed 2026-06-24) — 등급 ⓦ
- **Astra Pro (현행 series 페이지)**: Orbbec Astra Series, https://www.orbbec.com/products/structured-light-camera/astra-series/ (accessed 2026-06-24) — 현재 통합 "Astra Series" 표기로 모델별 분리 불명확, 일부 수치 단종 모델과 차이 → ⚠
- **Astra Pro (공식 GitHub)**: orbbec/ros_astra_camera, `launch/astra_pro.launch` (main), https://github.com/orbbec/ros_astra_camera (accessed 2026-06-24) — 공식 벤더 드라이버 설정. device PID(Product ID)·스트림 포맷 확인용 ✓. **단, launch default 해상도(640×480@30)는 드라이버 기본값이며 device spec 최대값 아님**(external_reference §3).

> **주의 1**: 다운로드 과정에서 `sodavision`이 `orbbec-astradatasheet-v3.0.pdf`로 제공한 파일은 실제로는 **Astra+** 데이터시트(Astra Pro 아님)였고, 이미지 전용 PDF라 본 비교에서 제외했다.
>
> **주의 2 (GitHub 확인 결과)**: 공식 Orbbec GitHub org(`orbbec/*`)에는 Astra Pro의 **SDK·ROS 래퍼·launch 설정·드라이버**는 있으나, FOV·치수·전력이 담긴 **단독 마케팅 datasheet PDF 는 호스팅되지 않는다**. GitHub 로 검증 가능한 항목(아래)은 ✓ 로 승격했다.

### GitHub 로 직접 검증된 Astra Pro 사실 (✓)

| 사실 | 값 | 출처 |
| --- | --- | --- |
| 컬러 카메라 방식 | UVC(USB Video Class) (별도 UVC stream), 포맷 MJPEG(Motion JPEG) | `astra_pro.launch`: `use_uvc_camera=true`, `uvc_camera_format=mjpeg` ✓ |
| USB VID(Vendor ID):PID (컬러 UVC) | 0x2BC5 : 0x0501 | `astra_pro.launch`: `uvc_vendor_id/uvc_product_id` ✓ |
| 깊이/IR(Infrared) 스트림 포맷 | 깊이 Y11, IR Y10 (16bit 미만 raw) | `astra_pro.launch`: `depth_format=Y11`, `ir_format=Y10` ✓ |
| ROS1 공식 지원 | Astra Pro 전용 launch 제공 | `orbbec/ros_astra_camera/launch/astra_pro.launch` 존재 ✓ |

---

## 1. 핵심 비교표

| 항목 | **Gemini E / E Lite** | **Astra Pro** |
| --- | --- | --- |
| 출시 세대 | 신형 (MX6000 ASIC) ✓ | 1세대 (~2016) · ~~단종~~ → **단종 여부 미확인** ⚠ⓦ [주1] |
| **깊이 기술** | 양안 구조광(Binocular structured light) ✓ | 단안 구조광(Monocular structured light), 940→800nm 스페클 ✓ⓦ |
| **측정 거리** | 0.2 m – 2.5 m ✓ | 0.6 m – 8 m (최적 0.6–6 m, 최소 0.443 m) ✓ⓦ |
| **깊이 해상도/프레임** | 최대 1024×768@5/10 fps · 640×480@30 fps ✓ | 640×480 (VGA) 16bit@30 fps ~~✓~~ → **⚠ 출처 미확정** [주2] |
| **깊이 FOV** | H 79° × V 62° × D 91° (±3°) ✓ | H 60° × V 49.5° × D 73° ⓦ |
| **깊이 정밀도** | 상대정밀도 1.1% @2000mm (중심 81% 영역) / 1.0% @1m ✓ | ~1 mm @근거리(0.6m), 평균오차 6.84mm @2.5m ⓦ |
| **RGB 카메라** | Gemini **E** 만 탑재 (E Lite 는 없음) ✓ | 탑재 (UVC) ✓ |
| **RGB 해상도/프레임** | 1920×1080@30fps(MJPEG)/@5fps(YUY2) — *Gemini E* ✓ | 1280×720@30 fps ~~✓~~ → **⚠ 출처 미상** [주3] |
| **RGB FOV** | 16:9 H 84.3° × V 53.6° × D 92.2° (±3°) ✓ | ~~(datasheet 미명시)~~ → **(공식 단독 datasheet 미수집 — 미확인)** ⚠ [주3] |
| **IR 센서** | 1280×800, Global Shutter, 940nm 협대역 ✓ | (Rolling Shutter, ~33ms) ⓦ |
| **베이스라인** | 40 mm ✓ | (Astra 동형 하우징) ⚠ |
| **인터페이스** | USB Type-C, USB 2.0 ✓ | USB 2.0 (Type-A) ✓ |
| **치수 (mm)** | 89.82 × 25.10 × 25.10 ✓ | 160 × 30 × 40 (ⓦ) / 165 계열 표기도 존재 ⚠ |
| **무게** | E 88.3g / E Lite 86.9g (±3g) ✓ | 약 300 g (0.3 kg) ⓦ |
| **소비전력** | E Lite 평균 <1.2W, 피크 <4.0W ✓ | 평균 ~2.2W(Full)/1.5W(Standby), 피크 1.85W ~ <2.4W (출처 간 편차) ⓦ⚠ |
| **동작 온도** | 10 ℃ – 40 ℃ ✓ | 10 ℃ – 40 ℃ ✓ |
| **레이저 등급** | Class 1 (940nm VCSEL) ✓ | Class 1 (구조광) ⓦ |
| **마이크** | 없음 ✓ | 2개 내장 ⓦ |
| **지원 OS** | Windows 10 / Android 8 / Ubuntu 18.04 ✓ | Windows / Linux / Android ✓ |
| **SDK** | OpenNI2 / ROS (Melodic 1.14.12) ✓ | Orbbec Astra SDK + OpenNI ✓ |
| **인증** | CE / FCC / RoHS 2.0 / Class 1 ✓ | (공식 datasheet 미수집) ⚠ |

### 2026-07-27 등급 감사 주석 (값 변경 없음 — 등급·서술만 정정)

- **[주1] Astra Pro "단종"** — 어느 출처도 단종을 진술하지 않는다. ⓦ 는 `:11` 정의상 "제3자 문서가 벤더 spec 을 인용"인데,
  해당 제3자 출처(`:18` ZMD Rev 0.1 Draft, 2016-09-24)는 단종 여부를 말할 수 없는 시점의 문서다.
  오히려 `:19` 는 현행 Orbbec Astra Series 페이지가 살아 있고 "모델별 분리 불명확"이라고만 적는다.
  → **"단종" 단정을 "단종 여부 미확인(2016 세대 모델, 현행 series 페이지에 모델별 표기 없음 `:19`)" 으로 완화.**
  이 단정은 `§2` 의 제품 선정 권고까지 전파되므로 그쪽도 함께 정정했다.
- **[주2] Astra Pro 깊이 640×480@30 의 ✓** — ✓ 는 `:10` 정의상 "1차 source(데이터시트 PDF) 직접 확인"인데,
  같은 문서 `:24` 가 "Astra Pro 의 … 단독 마케팅 datasheet PDF 는 호스팅되지 않는다", `:83` 이 "공식 단독 datasheet 미수집"이라고 적었다.
  GitHub 로 ✓ 승격된 항목은 `:30`–`:33` 의 4건(UVC/MJPEG, VID:PID, Y11·Y10 포맷, launch 존재)뿐이며 **깊이 해상도는 포함되지 않는다.**
  유일하게 확인 가능한 출처는 launch 기본값인데, `:20` 이 "launch default 해상도(640×480@30)는 드라이버 기본값이며 device spec 최대값 아님"이라고 스스로 배제했다.
  인용 PDF 도 저장소에 없다(출처 절의 2026-07-27 감사 박스 참조). → **✓ → ⚠(출처 미확정). 값은 그대로.**
- **[주3] Astra Pro RGB 1280×720@30 의 ✓ 및 RGB FOV 표기** — ✓ 근거가 될 출처가 목록에 없다:
  GitHub 검증 목록(`:30`–`:33`)에 RGB 해상도 없음, `:20` 은 launch 기본값이 640×480@30 이며 spec 최대값이 아니라고 명시, `:83` 은 공식 단독 datasheet 미수집.
  또한 원래 RGB FOV 칸의 "(datasheet 미명시)" 표현은 datasheet 를 열람한 것처럼 읽혀 `:24`·`:83` 의 "미수집" 서술과 어긋나므로 "미수집 — 미확인" 으로 표현을 일치시켰다.
  이 RGB 값은 `§2` 용도 비교로도 전파되므로 그쪽에 동일 표시를 달았다. → **✓ → ⚠(출처 미상). 값은 그대로.**

---

## 2. 용도 관점 요약

| 관점 | 우위 | 근거 |
| --- | --- | --- |
| **근거리 정밀 스캔 (0.2–2.5m)** | **Gemini E/E Lite** | 최소거리 0.2m, 깊이 1024×768, 상대정밀도 1.1% ✓ |
| **장거리/실내 내비게이션 (~8m)** | **Astra Pro** | 측정거리 0.6–8m ~~✓~~ → **✓ⓦ** [주4] — Gemini 는 2.5m 까지만 ✓ |
| **넓은 시야각(FOV)** | **Gemini E/E Lite** | 깊이 H79°×V62° vs Astra H60°×V49.5° ⓦ |
| **저전력/소형 임베디드** | **Gemini E/E Lite** | <1.2W·~87g·90mm vs ~2.2W·300g·160mm ✓ⓦ |
| **ROS2 / 최신 SDK 생태계** | **Gemini E/E Lite** (판정 유지) | ~~OpenNI2 + ROS Melodic 공식 지원 ✓ (Astra Pro 는 단종, 구형 SDK)~~ → **근거 교체** [주5] |
| **고품질 RGB 동시 스트림** | 대등 (Gemini E 1080p > Astra 720p) | Gemini E 1920×1080@30 ✓ vs Astra 1280×720@30 ~~✓~~ → **⚠ 출처 미상** [주3] (단, Gemini **E Lite 는 RGB 없음**) |
| **오디오(마이크) 필요** | **Astra Pro** | 마이크 2개 ⓦ (Gemini 없음) ✓ |

### 2026-07-27 등급 감사 주석 (§2)

- **[주4] 측정거리 등급 불일치** — 같은 문서의 원 항목 `§1 측정 거리` 는 동일 사실을 "0.6 m – 8 m (최적 0.6–6 m, 최소 0.443 m) **✓ⓦ**" 로 등급했는데,
  요약표에서는 ⓦ 가 빠지고 ✓ 단독으로 격상되어 있었다. Astra Pro 상세 spec 의 출처는 `:18` 의 제3자 ZMD 문서(ⓦ)이고 `:83` 은 공식 단독 datasheet 미수집이라고 적는다.
  → **원 항목과 동일한 `✓ⓦ` 로 되돌려 표기를 일치시켰다(값 변경 아님).**
- **[주5] "ROS2 / 최신 SDK 생태계" 근거 오배치** — 제시된 근거가 결론을 지지하지 않았다.
  **ROS Melodic 은 ROS1** 이므로 "ROS2 생태계" 우위의 근거가 될 수 없다(같은 문서 `§1 SDK` 도 "OpenNI2 / ROS (Melodic 1.14.12)", `§1 지원 OS` 도 Ubuntu 18.04 로 ROS1 세대 정보임을 보여준다).
  **정정된 근거(본 저장소 내 1차 확인 가능):**
  `src/Sensors/Camera/RGBD/OrbbecSDK_ROS2/README.MD:7` — "It supports ROS2 Foxy, Humble, and Jazzy distributions",
  `:784` — `| Gemini E | gemini_e.launch.py |`, `:785` — `| Gemini E Lite | gemini_e_lite.launch.py |`
  (2026-07-27 원문 대조 확인). 기존 "OpenNI2 + ROS Melodic 공식 지원"은 **ROS1 세대 정보**로 병기해 이력을 남긴다.
  또한 병기돼 있던 "Astra Pro 는 단종" 은 [주1] 대로 **단종 여부 미확인**이므로 선정 근거로 쓰지 말 것.
  → **우위 판정(Gemini E/E Lite) 자체는 유지, 근거 인용만 정정.**

---

## 3. 미확인 / 다음 검증 필요 (⚠ 항목)

- Astra Pro **치수**: 160×30×40 (ZMD ⓦ) vs 165 계열(현행 series 페이지) — 정본 datasheet 로 확정 필요.
- Astra Pro **소비전력**: 출처별 1.85W / 2.2W / <2.4W 편차 — 측정 조건(전체/대기/피크) 구분 필요.
- Astra Pro **RGB FOV·인증·베이스라인**: 공식 단독 datasheet 미수집 (단종 모델). 필요 시 Orbbec 레거시 datasheet 또는 기술지원 요청.
- 본 표의 Astra Pro ⓦ 항목은 제3자(ZMD) 문서 인용분 — Orbbec 1차 datasheet 와 대조 시 ✓ 로 승격 가능.
- **(2026-07-27 추가) 인용 1차 source PDF 본 저장소 미보관** — Gemini E&E Lite datasheet(루트 PDF), 텍스트 추출본 `References/orbbec/gemini-e-lite/`,
  `References/orbbec/astra-pro/Orbbec_Astra_Overview.pdf` 전부 부재(출처 절 감사 박스의 명령·결과 참조).
  **재수집·재대조 전까지 본 문서의 ✓ 는 검증 불가**이며, 이 문서를 근거로 부품 선정·설계 결정을 확정하지 말 것.
  필요한 조치: 원본 PDF 재수집 → `References/orbbec/**` 에 보관 → 페이지 인용과 함께 등급 재부여.
  (2026-08-04 정정: 폴더명은 `References/`(복수·대문자) 하나로 확정됐다 — external_reference §1. 위 감사 명령이 쓴 소문자 `ls references` 는 **당시 표기 분기 때문에 실패**한 것이며, 대문자 폴더는 그때도 존재했다. 부재 판정 자체(`orbbec/**` 없음)는 유효하다.)
