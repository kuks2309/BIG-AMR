# PGV...-F200/-F200A...-R4-V19 위치 응답 텔레그램(21바이트) 1회분.
# 근거: References/pepperl-fuchs/pgv/tdoct3707d_eng.pdf §5.1.2 (Table 5.1/5.2/5.3)

std_msgs/Header header

# --- 모드/상태 플래그 ---
bool tag_detected        # TAG=1: Data Matrix 태그 위 (x 는 부호 있음)
bool no_lane             # NL: 컬러 레인 미검출
bool no_position         # NP: 절대 X 위치 없음
bool repair_tape         # RP: 리페어 테이프 검출
uint8 lane_count         # LC: 0..3 (3 = 3개 이상)

# --- 위치 (해상도 파라미터 적용 후) ---
# 레인 추적: x 는 부호 없음, 태그 위: x 는 부호 있음 (매뉴얼 §5.1.2 Note "Sign")
float64 x_position_mm    # 코드 테이프 진행 방향 절대 위치
float64 y_offset_mm      # 레인 중심 대비 가로 편차 (부호 있음)
float64 angle_deg        # 각도 — DM 테이프: 절대각 0..360°, 컬러 테이프: 상대각 (§3.2 Angle Output)

# --- 원시값 (스케일 미적용, 진단·재처리용) ---
int64 x_raw              # XP/XPS 24bit (태그 모드에서 부호확장 완료)
int32 y_raw              # YPS 14bit (부호확장 완료)
uint32 angle_raw         # ANG 14bit

# --- 태그/제어 코드 ---
uint32 tag_number        # tag_detected=1 일 때 TAG_00..27
bool cc1_detected        # CC1 플래그 (byte 1)
bool cc2_detected        # CC2 플래그 (byte 1)
uint16 control_code1     # 레인 모드 CC1 번호 (001..999)
uint16 control_code2     # 레인 모드 CC2 번호
uint8 orientation1       # O1: 0..3 = 상행 레인 기준 0/90/180/270° 시계방향 (§5.1.2.2)
uint8 orientation2       # O2
uint8 side1              # S1: 0=없음 1=레인 우측 2=레인 좌측 3=판별불가 (§5.1.2.3)
uint8 side2              # S2

# --- 방향 결정 상태 (응답 byte 2 의 LL/RL) ---
bool left_lane_selected
bool right_lane_selected

# --- 진단 ---
bool warning             # WRN 플래그 (byte 1)
uint16 warning_bits      # WRN00..13 (Table 5.5)
bool error               # ERR 플래그 — 1 이면 위치 필드 무효, error_code 참조
uint32 error_code        # ERR=1 일 때 XP 필드에 실린 코드 (Table 5.4: 2/5/6/>1000)
