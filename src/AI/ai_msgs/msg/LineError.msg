# 라인 추종 횡오차 (line_seg_node → 라인 추종 제어기)
#
# 미검출 프레임도 발행한다 — 제어기가 라인 소실을 즉시 감지해야 하므로
# 침묵은 정지 신호가 될 수 없다.

std_msgs/Header header      # 원본 이미지 stamp 승계 (지연 판단용)
bool    detected            # 라인 검출 여부
float32 offset              # 제어 기준행 횡오차, 정규화 [-1,1], + = 진행방향 기준 오른쪽
float32 angle               # 라인 기울기 [rad], 수직 = 0, + = 위쪽이 오른쪽으로 기움
float32 confidence          # seg 신뢰도 (미검출 시 0)
string  camera              # 이 오차를 만든 카메라 논리명 (cam_f = 전진 / cam_r = 후진)
