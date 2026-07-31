# 한 프레임의 검출 결과 묶음.
#
# header.stamp 는 **원본 프레임의 취득 시각**을 그대로 승계한다(추론 완료 시각이 아니다).
# 소비자가 검출을 그 시점의 로봇 자세·오도메트리와 맞출 수 있어야 하기 때문이다.

std_msgs/Header header

string camera            # 카메라 논리 이름 (예: "cam0")
uint32 image_width       # 원본 프레임 폭 — 좌표 정규화가 필요한 소비자용
uint32 image_height      # 원본 프레임 높이
float32 inference_ms     # 이 프레임의 추론 소요(ms). 성능 감시·부하 조절용
float32 latency_ms       # 프레임 취득 → 발행까지 지연(ms). 실시간성 판단용

Detection[] detections
