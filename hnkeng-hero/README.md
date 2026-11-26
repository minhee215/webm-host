# HNKENG 메인 히어로 배경 영상 (2026 리뉴얼, 무드보드 v4)

HNK ENG 무드보드(AI · ROBOTICS · AUTOMATION / Engineering a Smarter Tomorrow)의 핵심 이미지 5종을 실사풍 18초 영상으로 만들었습니다.
인물은 뒷모습으로만 등장하고, 텍스트·로고는 HTML로 분리했습니다. 현재 출력은 480p 샘플입니다.

## 폴더 구성

| 경로 | 설명 |
|---|---|
| `stills/01~05.jpg` | 장면별 실사풍 스틸 (GPT Image 2.6, 2688×1520에서 JPG 변환) |
| `clips/01~05.mp4` | 스틸을 첫 프레임으로 생성한 5초 동작 클립 (Kling 3.0 Standard, 720p 24fps, 무음) |
| `build/edit.py` | 편집·색보정·그레인·인코딩 스크립트 (Pillow/NumPy + FFmpeg) |
| `build/stabilize.py` | 서브픽셀 위상상관 기반 손떨림 보정 (생성 클립의 미세 흔들림 제거) |
| `build/dashboard.py` | 4번 대시보드 장면: 스틸 기반, KPI 숫자를 Inter Display로 다시 조판하고 매끄러운 디지털 카메라 무빙 적용 |
| `dist/hero-video.mp4` | 마스터 H.264 (샘플 854×480) |
| `dist/hero-video-web.mp4` | 웹용 H.264 (샘플 854×480) |
| `dist/hero-video-web.webm` | 웹용 VP9 (샘플 854×480) |
| `dist/hero-video-mobile.mp4` | 모바일용 H.264 640×360 (767px 이하에서 자동 선택) |
| `dist/hero-poster.jpg / .webp` | 첫 프레임 포스터 |
| `component/hero-section.html` | 아임웹 코드 위젯용 반응형 히어로 컴포넌트 |
| `index.html` | 미리보기 페이지 |

## 장면 구성 (18.0초, 24fps, 하드 컷)

| 구간 | 장면 | 무드보드 항목 | 동작 / 카메라 |
|---|---|---|---|
| 0.00–3.83 | 01 | AMR 자율주행로봇 | AMR이 상자를 싣고 주행, 배경 로봇 작업 / 로우앵글 트래킹 |
| 3.83–7.62 | 02 | 데이터 센터 | 서버 LED 점멸 / 통로를 따라 전진 |
| 7.62–11.50 | 03 | MCC 제어반 | 표시등 점멸, HMI 갱신 / 패널을 따라 측면 이동 |
| 11.50–14.79 | 04 | 현장설비 소프트웨어(대시보드) | KPI 숫자가 선명하게 조금씩 갱신 / 모니터로 부드럽게 푸시 인 (스틸 기반 렌더링) |
| 14.79–18.00 | 05 | 사람이 제어하는 모습 | 엔지니어(뒷모습)가 태블릿을 가슴 높이에서 안정적으로 들고 확인, 로봇 라인 가동 / 어깨 너머로 전진 |

생성 클립 4개(01·02·03·05)는 모두 `build/stabilize.py`로 미세 흔들림을 제거한 뒤 편집합니다.

## 다시 렌더링

```bash
pip install pillow numpy
python3 build/edit.py                              # 854x480 샘플
python3 build/edit.py --width 1280 --height 720    # 720p
```

컷 길이와 시작 프레임은 `build/edit.py`의 `SHOTS` 표에서 조정합니다. 1080p 본편은 클립을 Kling Pro 등 1080p로 다시 생성한 뒤 `--width 1920 --height 1080`으로 렌더링합니다.

## 아임웹 적용

1. `dist/` 파일을 공개 URL에 올립니다.
2. `component/hero-section.html` 전체를 코드 위젯에 붙여넣고 `data-webm`, `data-mp4`, `data-mobile`, 포스터 `srcset`/`src`를 절대 URL로 바꿉니다.
3. 섹션이 폭 제한 컨테이너 안에 있으면 `hnk-hero hnk-hero--bleed` 클래스를 씁니다.
