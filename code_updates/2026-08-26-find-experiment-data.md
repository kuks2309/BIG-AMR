# 2026-08-26 — Tools/find_experiment_data.sh 신설

## 무엇을

실험 데이터 전수 검색기 신설. 날짜(YYMMDD 또는 YYYY-MM-DD)를 받아 저장소와
/home/nvidia 전체를 깊이 제한 없이 훑어 ① 이름에 날짜 토큰이 든 파일, ② 그날
생성·수정된 bag(.db3/.mcap/metadata.yaml)·jsonl·csv·리포트(html/pdf)를 열거한다.
두 절이 모두 비어야만 "데이터 부재"를 보고할 수 있다고 출력 말미에 명시.

## 왜

"어제 rosbag 있나" 질문에 maxdepth 5/4 제한 검색 0건으로 "없다"를 보고했다가
실재 5개(≈1.7 GB)를 놓친 사건(docs/claude-mistake/2026-08-26-001)의 재발 방지.
깊이·경로 제한 검색의 0건은 부재의 근거가 될 수 없으므로, 부재 보고 전 반드시
이 스크립트를 돌리도록 절차를 도구화했다.

## 검증

`bash Tools/find_experiment_data.sh 260825` 실기 실행 — 어제 놓쳤던 bag 5개
디렉토리와 jsonl·리포트가 모두 출력됨을 확인. 주석의 이력성 문구는
comment-gate 지적으로 원칙 서술로 교정(이력은 본 entry 가 담당).
