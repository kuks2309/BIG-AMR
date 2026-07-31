# 단일 객체 검출 결과.
#
# 좌표는 **원본 이미지 픽셀** 기준(좌상단 원점). 추론은 imgsz 로 축소해 수행하지만
# 발행 전에 원본 해상도로 되돌린다 — 소비자가 카메라 영상과 직접 겹칠 수 있어야 한다.
#
# vision_msgs/Detection2D 를 쓰지 않는 이유: ros-humble-vision-msgs 가 이 호스트에
# 미설치이고 설치에 root 권한이 필요하다. 저장소 선례(trnav_msgs)를 따라 자체 정의한다.

string class_name        # 모델 클래스 이름 (예: "person")
int32 class_id           # 모델 클래스 인덱스 (COCO 사전학습이면 person=0)
float32 confidence       # 0.0 ~ 1.0

int32 x                  # 바운딩박스 좌상단 x (픽셀)
int32 y                  # 바운딩박스 좌상단 y (픽셀)
int32 width              # 폭 (픽셀)
int32 height             # 높이 (픽셀)
