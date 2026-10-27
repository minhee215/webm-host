# Reference Analysis — AXCORE 2분 홍보영상 Preview

분석 대상
- `레퍼런스4.mp4` — 1920×1080, 30fps, 76.7s (법률 AI SaaS 제품 필름, 다크 테크 + UI)
- `레퍼런스5.mp4` — 1328×732, 30fps, 19.1s (실사 + Environmental UI 합성)

분석 방법
- 레퍼런스4: 2fps 콘택트 시트(153프레임) + FFmpeg scene-change(threshold 0.25) 컷 검출
- 레퍼런스5: 4fps 콘택트 시트(76프레임) + 동일한 컷 검출
- 컷 검출 결과 (s)
  - Ref4: 2.03 / 3.83–4.57(파일 폭발 구간, 연속 고속 변화) / 11.83–12.70 / 21.17 / 23.97 / 28.97 / 36.10 / 37.57 / 46.70–46.90 / 49.50 / 52.50 / 56.83 / 60.17 / 66.20 / 70.43 / 75.80
  - Ref5: 0.67 / 2.20 / 3.73 / 5.13 / 5.83 / 8.03 / 10.47 / 11.90 / 17.70

> 두 영상의 로고·브랜드명·문구·그래픽 에셋은 사용하지 않는다. 아래 분석은 Visual Grammar와 Motion Direction만 추출한 것이다.

---

## 1. 레퍼런스4 — Timeline Breakdown

| TC | 장면 | 핵심 연출 | 전환 방식 |
|---|---|---|---|
| 0.0–2.0 | 다크 네이비 공간, 폴더 아이콘 + 커서 | 커서 클릭이 첫 Motion Trigger | 클릭 → 오브젝트 폭발 (Match-on-action) |
| 2.0–4.6 | 문서 페이지 수십 장이 화면을 가득 채움 | Object multiplication, Z-depth 분산 | 문서가 축소되며 원형 배열로 정렬 |
| 4.6–7.0 | 사각형 문서 → 원형 링 → 이중 Orbit | **Shape Morphing**: 사각형 점 → 라인 → 타원 → 심볼 | 심볼이 화면 중앙에 수렴 |
| 7.0–9.5 | 심볼 + 타이틀 타이포 Reveal | 심볼이 좌측으로 이동하며 Wordmark 공간 확보 | 심볼이 다음 장면 Focus Point로 남음 |
| 9.5–12.0 | 섹션 타이틀 + 가는 Orbit 원들이 부유 | 작은 Star Symbol이 Line 위를 이동 | 다크 배경 위 UI 카드가 등장 |
| 12.0–15.0 | 다크 → 화이트 UI | **UI Card Push-in**: 카드가 화면을 덮으며 밝은 공간이 됨 | Card scale-up (밝기 전환을 오브젝트로 해결) |
| 15.0–20.0 | 파일 Chip이 입력창으로 날아옴, 전송 클릭 | 파일 Chip들이 심볼 주변 Orbit으로 재배열 | 클릭 → 처리 상태 리스트 |
| 20.0–24.0 | 문서 페이지 확대, 텍스트 Highlight Pill | Push-in + 부분 Highlight (OCR식 추출) | 페이지 스택 넘김 |
| 24.0–29.0 | 화이트 공간의 Floating Pill 태그 | Camera Pan + Parallax (태그 레이어별 속도 차) | 다크로 Pull-out |
| 29.0–37.5 | 다크 UI: 입력 → 선택지 → 선택(Highlight) | 커서 클릭 → 선택 항목 Cyan Fill | 선택 결과 카드가 밝은 화면으로 확장 |
| 37.5–46.7 | 장문 결과 문서 Scroll | 수직 Pan + 약한 Perspective Tilt, 가장자리 블루 그라디언트 | 다크 섹션 타이틀로 Cut on beat |
| 46.7–52.5 | Split layout: 좌측 리스트 / 우측 큰 숫자 | 숫자 Count-up (Rolling digits) | 섹션 타이틀 |
| 52.5–56.8 | 문서 창 오픈 → Scroll | 모달 Scale-in + 내부 Scroll | 블루 그라디언트 섹션으로 |
| 56.8–66.2 | 동심원 → 타원 배열 → 구(Wire) → X Orbit → 심볼 | **연속 Shape Morphing**, 중앙 키워드만 교체 | 심볼로 수렴 |
| 66.2–75.8 | 다크 + 하단 지평선 Arc, 심볼 + 타이틀 Glow | Calm Hold, 미세 Bloom | 화이트 로고 카드 |

## 2. 레퍼런스5 — Timeline Breakdown

| TC | 장면 | 합성 방식 | 전환 방식 |
|---|---|---|---|
| 0.0–4.4 | 카페, 휴대폰에 말하는 인물 | 음성 텍스트 Pill이 머리 옆 공간에 고정, Cyan Light Ribbon이 인물 주변을 감쌈 | 인물 시선 → 휴대폰 (Match-on-action) |
| 4.4–5.1 | Top-down, 손에 든 휴대폰 | **Screen Replacement** + 휴대폰이 카메라로 다가옴 (Push-in) | 휴대폰 화면 → 와이드 |
| 5.1–5.8 | 카페 와이드 | 분석 텍스트가 창문 유리면에 Perspective로 부착 | Cut on motion |
| 5.8–8.0 | 키보드 타이핑 Close-up → 얼굴 Close-up | Light Ribbon이 컷을 넘어 같은 방향으로 계속 흐름 (**Graphic Continuity**) | Ribbon이 전환 매개 |
| 8.0–10.4 | 반투명 브라우저 UI가 얼굴 위 | 모니터 내부 POV (Reverse Angle UI) | UI Card Blur-push |
| 10.4–11.9 | 로우앵글 사무실 | UI 카드들이 천장 평면에 **Planar 배치** (Perspective Warp) | 손가락 터치 |
| 11.9–14.0 | 유리 버튼을 누르는 손가락 | 버튼 Pill 뒤에서 촬영(미러 텍스트), 터치 Ripple | Ripple → 다음 장면 |
| 14.0–17.7 | 밝은 오피스, 발표자 | 창문 평면에 Bar/Grade 패널 합성, 카메라 Dolly에 맞춘 **Parallax** | Light Ribbon |
| 17.7–19.1 | 고층 빌딩 로우앵글 | 하늘을 가로지르는 Ribbon | End |

---

## 3. 항목별 분석

### 3.1 Color
- Ref4 Dark: 배경은 순수 블랙이 아닌 `#03061A → #0A1550` 수직/방사 그라디언트, 중앙 하단에 약한 Blue Bloom. 블루 섹션은 `#0A2BD8 → #2F7BFF` 대각 그라디언트.
- Ref4 Bright UI: `#FFFFFF / #F5F7FB`, 얇은 `#E3E7EF` 보더, 포인트 블루. 화이트 화면 하단에도 하늘색 그라디언트가 깔려 "공간"이 유지됨.
- Ref5: 실사는 자연광 High-key, 웜뉴트럴. 브랜드 일관성은 **Cyan/Blue Light Ribbon과 화이트 반투명 UI**로만 유지.
- AXCORE 적용 팔레트 (로고 PNG에서 추출한 실제 값 `#0053FC` 기준)
  - Deep Navy `#040817`, Navy `#0A1430`, AXCORE Blue `#0053FC`, Light Blue `#5B8CFF`, Ice `#CFE0FF`, White `#FFFFFF`, Cool Gray `#8A94A8`, Surface `#F4F6FA`, Border `#E2E7F0`
  - 레퍼런스4의 Purple 계열은 제외 (AXCORE 아이덴티티와 충돌).

### 3.2 Camera
- 거의 모든 카메라는 **한 방향으로 지속되는 느린 이동**(Push-in, Lateral Pan, Vertical Scroll)이다. 정지 카메라는 타이틀 Hold 구간에만 쓰인다.
- UI 장면에서 카메라는 "UI 위를 비행"한다. UI 전체를 보여주기보다는 Crop 상태로 진입해 필요한 요소로 Pan/Push하고, 마지막에 Pull-out해 전체 구조를 보여준다.
- 실사(Ref5)는 Dolly / Push-in / Low angle 위주이며, 합성 UI는 카메라 이동과 반대 방향의 Parallax를 갖는다.

### 3.3 Graphic
- 선(1–2px), 점, 링, 타원 Orbit, 작은 Star Symbol만으로 구성. 3D 오브젝트는 거의 없음.
- 그래픽 요소는 장식이 아니라 **다음 장면의 구조물**로 변환된다 (문서 → 점 → 링 → 심볼).
- 글로우는 선의 2–3배 폭의 저강도 Bloom이며 화면 전체를 밝히지 않는다.

### 3.4 UI
- 실제 제품 UI를 Screenshot으로 붙이지 않고, 요소 단위(입력창, Chip, 리스트, 카드, 숫자)로 분해해 모션을 준다.
- UI 요소가 날아오고(Chip), 정렬되고(리스트), 강조되고(Highlight Pill), 결과로 변환된다(문서). 원인 → 결과 관계가 명확.
- 선택 행위는 커서 클릭 → Fill Color 변화 → 다음 상태로 즉시 연결.

### 3.5 Motion
- Easing: 대부분 Ease-out 계열(빠르게 출발, 길게 감속). 진입 400–700ms, 이동 800–1500ms. 바운스 없음.
- 텍스트: 글자 단위가 아닌 **줄 단위 Fade + 8–12px 상승**, 혹은 좌→우 마스크 Reveal.
- 숫자: Rolling Count-up.
- Motion Blur: 파일 Chip 비행, 빠른 Pan 구간에서만 사용.

### 3.6 Transition (가장 중요)
반복적으로 쓰인 전환 문법은 다음 6가지다. Cross dissolve / Glitch / Spin은 사용되지 않았다.
1. **Object → Shape Morph**: 문서 묶음 → 원형 점 배열 → 링 → 심볼
2. **Symbol as Anchor**: 작은 심볼이 남아 다음 장면의 Focus Point가 됨
3. **UI Card Push-in**: 다크 공간의 카드에 Push-in → 카드 내부가 다음 화면
4. **Pull-out to Space**: UI에서 Pull-out하면 다시 다크 공간
5. **Graphic Continuity across Cuts** (Ref5): Light Ribbon이 컷을 넘어 같은 방향, 같은 속도로 흐름
6. **Match-on-action** (Ref5): 손/시선/휴대폰의 움직임이 다음 컷의 시작 동작

### 3.7 Typography
- 한글 산세리프(Pretendard 계열과 유사), SemiBold 타이틀 + Regular 서브. 자간은 기본값이며 넓히지 않음.
- 타이틀 크기는 화면 높이의 약 4–5%, 서브는 2.5%. 한 화면 1–2줄.
- 하단 나레이션 자막이 상시 존재하지만, 본 프로젝트에서는 **제외**한다(요구사항).

### 3.8 Sound (오디오 트랙 수치 분석)
- Ref5 오디오 트랙은 무음(전 구간 digital silence)이므로 사운드 기준은 Ref4만 사용한다.
- Ref4: Peak −15.3 dBFS, 평균 RMS −36.2 dB. 5초 구간 RMS 편차가 −38.6 ~ −33.8 dB로 **약 5 dB 범위에서만 변한다**. 즉, 음악이 화면을 압도하지 않는 낮은 레벨의 일정한 베드이며, 섹션 경계에서 미세하게 상승한다.
- 스펙트럼 중심(Spectral centroid)은 2.4–4.2 kHz, 후반(60s 이후)에 상승한다. 후반으로 갈수록 밝은 고역 레이어가 추가되는 구조다.
- RMS가 6 dB 이상 순간 상승하는 Onset은 0.5–3초 간격이며 UI 이벤트(클릭, 파일 등장, 전송)와 일치한다. SFX가 모든 모션이 아니라 **행위(Action)**에만 붙는다는 의미다.
- AXCORE 적용: BGM −20 LUFS 수준의 낮은 베드(나레이션 Headroom 확보), 섹션마다 레이어 추가로 에너지 상승, SFX는 클릭/스캔/연결/노드 활성 같은 행위에만.

### 3.9 Scene Rhythm
- Ref4: 섹션 타이틀(3–4s) → 제품 데모(6–10s) → 섹션 타이틀의 반복. 평균 샷 길이 약 4.5s.
- Ref5: 평균 샷 길이 약 2.1s. 실사 몽타주는 빠르지만, Ribbon/UI가 연속되어 끊겨 보이지 않음.
- AXCORE 적용: 설명 장면(S03, S04)은 Ref4의 길고 연속적인 UI 카메라, 실사 장면(S01, S05, S06)은 Ref5의 2–4s 리듬.

---

## 4. AXCORE에 적용할 Motion Grammar (결론)

| 규칙 | 내용 |
|---|---|
| G1. One Camera | 영상 전체를 하나의 가상 카메라가 이동하는 것으로 설계. 장면 경계에서 카메라 속도 벡터를 유지한다. |
| G2. Diamond Anchor | 로고의 45° Blue Diamond를 Core Node로 사용 (Data Node → Cursor → Analysis Point → Connector Node → Ontology Core → Logo). 매 장면 등장시키지 않음. |
| G3. Line Continuity | 1px Blue Line이 장면을 넘어 이어진다 (선 → 모니터 엣지 → 데이터 연결선 → Workflow → 예측 그래프 → 센서 라인 → 제어 라인). |
| G4. Card Push / Pull | 밝기 전환(다크 ↔ 화이트)은 반드시 UI 카드의 Push-in/Pull-out로 해결. |
| G5. Environmental UI | 실사 위 UI는 Planar Tracking + Perspective로 공간에 부착. 화면 고정 오버레이 금지. |
| G6. Cause & Effect | 모든 UI 모션은 이전 동작의 결과로 발생 (업로드 → 분류 → 점수 → 워크플로우 → 과제 → 로드맵). |
| G7. Calm Easing | Ease-out cubic/quint 기본, Overshoot 금지, Spring 미사용. |
