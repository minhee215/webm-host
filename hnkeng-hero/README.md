# HNKENG 메인 히어로 영상

"INTELLIGENCE IN MOTION — 산업을 이해하는 기술, 미래를 연결하는 지능"

## 폴더 구성

| 경로 | 설명 |
|---|---|
| `src/` | 원본 이미지 5장 (scene01~05) |
| `clips/s1~s5.mp4` | 원본 이미지를 첫 프레임으로 Kling 3.0(Higgsfield)에서 생성한 5초 동작 클립, 1280×720 24fps |
| `build/edit.py` | 매치컷 편집 스크립트 (구간 선택 → 컷 정렬용 리프레이밍 → 색보정·그레인 → FFmpeg 인코딩) |
| `dist/hero-video.mp4` | 마스터 H.264 (CRF 18, 고화질) |
| `dist/hero-video-web.mp4` | 웹 최적화 H.264 (CRF 25, 비트레이트 상한) |
| `dist/hero-video-web.webm` | 웹 최적화 VP9 (2-pass, CRF 38) |
| `dist/hero-poster.jpg / .webp` | 영상 첫 프레임 포스터 |
| `component/hero-section.html` | 아임웹 코드 위젯에 붙여넣는 반응형 히어로 컴포넌트 |
| `index.html` | 컴포넌트 미리보기 페이지 |

## 장면 구성 (총 18.0초, 24fps, 하드 컷 + 매치컷)

| 구간 | 장면 | 동작 / 카메라 | 다음 장면으로의 매치컷 |
|---|---|---|---|
| 0.00–3.42초 | 01 화학·소재 플랜트 | 증기 상승, 구름 이동 / 크레인 업 + 돌리 인, 끝에서 푸시 | 수직 철골 기둥 → 제어반 수직 프레임 |
| 3.42–7.00초 | 02 PLC 제어반 | LED 점멸 / 우측 슬라이드 + 푸시 인 | 초록 PLC LED → 초록 타워 램프 (같은 화면 위치) |
| 7.00–10.42초 | 03 자동화 생산라인 | 로봇 팔 픽앤플레이스, 컨베이어 이동 / 측면 트래킹 | 지나가는 전경 기둥 → 제어실 창틀 (같은 x 위치) |
| 10.42–14.21초 | 04 HMI·SCADA 제어실 | 트렌드 그래프·게이지 갱신, 작업자 뒷모습 / 아크 + 화면으로 푸시 인 | P&ID 화면의 탱크 심볼 → 실제 탱크 |
| 14.21–18.00초 | 05 스마트팩토리 | 로봇 셀 동작 / 탱크에서 풀백 + 크레인 업 | (루프) 넓은 왼쪽 벽 → 넓은 왼쪽 하늘 |

## 다시 렌더링

```bash
pip install pillow numpy
python3 build/edit.py                                          # 854x480 샘플
python3 build/edit.py --width 1920 --height 1080 --out dist-1080     # 고해상도
```

생성 클립이 720p라 1080p 본 제작은 클립을 1080p(Kling Pro 등)로 다시 생성한 뒤 같은 스크립트로 편집하는 것을 권장합니다. 컷 정렬 값(`SEGMENTS`의 keys)은 클립이 바뀌면 다시 측정해야 합니다.

## 아임웹 적용

1. `dist/` 파일을 공개 URL에 올립니다 (아임웹 파일 업로드, 또는 이 저장소를 jsDelivr로 서빙).
2. `component/hero-section.html` 전체를 코드 위젯에 붙여넣고, `data-webm`, `data-mp4`, 포스터 `srcset`/`src` 4곳을 절대 URL로 바꿉니다.
3. 섹션이 폭 제한 컨테이너 안에 있으면 `<section class="hnk-hero hnk-hero--bleed">`로 전체 폭을 사용합니다.
