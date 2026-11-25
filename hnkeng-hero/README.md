# HNKENG 메인 히어로 영상

"INTELLIGENCE IN MOTION — 산업을 이해하는 기술, 미래를 연결하는 지능"

## 폴더 구성

| 경로 | 설명 |
|---|---|
| `src/` | 원본 이미지 5장 (scene01~05) |
| `build/render.py` | 렌더링 스크립트 (Pillow/NumPy로 프레임 생성 → FFmpeg 인코딩) |
| `dist/hero-video.mp4` | 마스터 H.264 (CRF 18, 고화질) |
| `dist/hero-video-web.mp4` | 웹 최적화 H.264 (CRF 25, 비트레이트 상한) |
| `dist/hero-video-web.webm` | 웹 최적화 VP9 (2-pass, CRF 38) |
| `dist/hero-poster.jpg / .webp` | 영상 첫 프레임 포스터 |
| `component/hero-section.html` | 아임웹 코드 위젯에 붙여넣는 반응형 히어로 컴포넌트 |
| `index.html` | 컴포넌트 미리보기 페이지 |

## 장면 구성 (총 18.0초, 30fps, 크로스 디졸브 0.8초)

| 구간 | 장면 | 카메라 |
|---|---|---|
| 0–3초 | 01 화학·소재 플랜트 | 줌 1.12 고정, 좌→우 수평 이동 |
| 3–7초 | 02 PLC 제어반 | 1.04→1.15 미세 줌인, LED 일부 점멸 |
| 7–11초 | 03 자동화 생산라인 | 줌 1.12 고정, 우→좌 측면 이동 (로봇 변형 없음) |
| 11–15초 | 04 HMI·SCADA 제어실 | 1.06→1.11 미세 줌 + 수평 드리프트 |
| 15–18초 | 05 스마트팩토리 | 1.16→1.04 줌아웃 → 17.2초부터 01로 디졸브(루프) |

## 다시 렌더링

```bash
pip install pillow numpy scipy
python3 build/render.py                                        # 854x480 샘플
python3 build/render.py --width 1920 --height 1080 --out dist-1080   # 본 제작
```

원본 이미지가 1672×941이라 1080p 출력 시 약 1.3배 업스케일됩니다. 본 제작 전 2K 이상 원본을 받는 것을 권장합니다.

## 아임웹 적용

1. `dist/` 파일을 공개 URL에 올립니다 (아임웹 파일 업로드, 또는 이 저장소를 jsDelivr로 서빙).
2. `component/hero-section.html` 전체를 코드 위젯에 붙여넣고, `data-webm`, `data-mp4`, 포스터 `srcset`/`src` 4곳을 절대 URL로 바꿉니다.
3. 섹션이 폭 제한 컨테이너 안에 있으면 `<section class="hnk-hero hnk-hero--bleed">`로 전체 폭을 사용합니다.
