# HNKENG 메인 히어로 배경 영상 (2026 리뉴얼)

브랜드 방향 "사람 · 데이터 · 로봇 · 자동화의 연결"을 밝은 실사풍 18초 영상으로 표현합니다.
HNK의 사업 영역 하나당 한 장면, 총 5장면이며 카메라가 계속 오른쪽으로 흐르게 해 하나의 연결된 흐름으로 읽히도록 했습니다. 텍스트·로고는 HTML로 분리했습니다.

## 폴더 구성

| 경로 | 설명 |
|---|---|
| `stills/01~05.jpg` | 장면별 실사풍 스틸 (GPT Image 2.6, 2688×1520에서 JPG 변환) |
| `clips/01~05.mp4` | 스틸을 첫 프레임으로 생성한 5초 동작 클립 (Kling 3.0 Standard, 720p 24fps, 무음) |
| `build/edit.py` | 편집·색보정·그레인·인코딩 스크립트 (Pillow/NumPy + FFmpeg) |
| `dist/hero-video.mp4` | 마스터 H.264 1280×720 (CRF 17) |
| `dist/hero-video-web.mp4` | 웹용 H.264 1280×720 |
| `dist/hero-video-web.webm` | 웹용 VP9 1280×720 |
| `dist/hero-video-mobile.mp4` | 모바일용 H.264 640×360 (767px 이하에서 자동 선택) |
| `dist/hero-poster.jpg / .webp` | 첫 프레임 포스터 |
| `component/hero-section.html` | 아임웹 코드 위젯용 반응형 히어로 컴포넌트 |
| `index.html` | 미리보기 페이지 |

## 장면 구성 (18.0초, 24fps, 하드 컷)

| 구간 | 장면 | 내용 | 연결 요소 | 사업 분야 |
|---|---|---|---|---|
| 0.00–3.58 | 01 | 화학 플랜트, 엔지니어가 PLC 판넬 앞에서 태블릿 실시간 데이터 확인 | 사람 + 데이터 + 제어 | 프로세스 (PLC·DCS·전계장) |
| 3.58–7.21 | 02 | 전동컴프레서 조립라인, 작업자가 HMI를 터치하자 생산 데이터 갱신 | 데이터 + 자동화 | 제어/FA |
| 7.21–10.79 | 03 | 협동로봇이 부품을 비전 카메라로 검사 후 트레이에 배치 (인물 없음) | 로봇 + 데이터 | Robotics·AI 비전 |
| 10.79–14.42 | 04 | AMR이 배터리 모듈을 싣고 로봇 셀 사이를 이동 | 로봇 + 자동화 + 사람 | 2차전지·물류 자동화 |
| 14.42–18.00 | 05 | 메자닌에서 엔지니어 둘이 태블릿을 보며 연결된 공장 전체를 내려다봄 | 전체 연결 | 스마트팩토리 |

## 다시 렌더링

```bash
pip install pillow numpy
python3 build/edit.py
```

컷 길이와 시작 프레임은 `build/edit.py`의 `SHOTS` 표에서 조정합니다. 1080p 본편은 클립을 Kling Pro 등 1080p로 다시 생성한 뒤 `--width 1920 --height 1080`으로 렌더링합니다.

## 아임웹 적용

1. `dist/` 파일을 공개 URL에 올립니다.
2. `component/hero-section.html` 전체를 코드 위젯에 붙여넣고 `data-webm`, `data-mp4`, `data-mobile`, 포스터 `srcset`/`src`를 절대 URL로 바꿉니다.
3. 섹션이 폭 제한 컨테이너 안에 있으면 `hnk-hero hnk-hero--bleed` 클래스를 씁니다.
