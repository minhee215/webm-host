# Storyboard — AXCORE 2분 홍보영상 (480p Preview v01)

- 총 길이 120.0s / 30fps / 3,600 frames / 854×480
- 나레이션 음성·자막은 넣지 않는다. 아래 Narration은 타이밍 설계 기준이다.
- 모든 전환은 Effect가 아니라 Camera / Object / Graphic Match로 해결한다. 각 샷의 `Out` 과 다음 샷의 `In` 은 같은 Motion Vector 또는 같은 오브젝트를 공유한다.
- 화면 텍스트는 Keyword / UI Label / Data Label만 사용한다.
- 숫자는 IR Deck에 실제로 존재하는 데모 기업 값(AX 5대 지수 34.1 / 56.3 / 45.0 / 47.2 / 25.0, 종합 41.52점, Lv.2, 과제 22개, +8.6점, 수집 48건)만 사용한다. 그 외 값은 사용하지 않거나 `DEMO` 라벨을 붙인다.

### v01 제작 중 반영된 변경
- 웹 기반 서비스이므로 **태블릿·휴대폰 사용 장면은 제외**했다.
  - 1C: 작업자의 태블릿을 **종이 작업지시서 클립보드**로 바꿨다. 1C→1D Match Cut은 클립보드 → 책상 위 점검표로 연결한다.
- 일부 UI 구간은 **블러 처리한 스톡/모션 배경** 위에 놓았다.
  - S03 진단·워크플로우: 회의실 V4
  - S03 과제·로드맵·보고서: Orbit 모션
  - S04 워크스페이스: 공장 V2
  - S05 답변 패널: 사무실 V8을 랙 포커스로 흐리게 처리
  - S06 수요 예측: 사무실 V1
- S04 온톨로지(64.2–73s)는 **이전 작업에서 만든 온톨로지 영상**을 원본 그대로 사용한다. 수렴점에서 원형 마스크로 열리며 시작한다.
- S05 실사는 같은 인물의 와이드 샷 **V8**로 바꿨다. 모니터 옆 창 평면에 Source 패널을 배치하기 위해서다.
- 미반영(v02 예정)
  - S03: '문서에서 업무 추출 → 우선순위 재배치' 모션
  - S04: 기능 토글로 워크스페이스를 구성하는 표현, 스캔 라인이 손글씨를 필드로 바꾸는 OCR 표현

표기: `V#` = Kling 4.0 Image-to-Video 실사 플레이트, `K#` = Nano Banana Pro 키프레임, `MG` = Python Motion Graphic, `UI` = Python으로 재구성한 AXpoint UI

---

## SCENE 01 — 0.0–15.0s · "어디에 AI를 적용할 것인가"
Narration: AI가 기업의 일하는 방식을 빠르게 바꾸고 있습니다. 하지만 중요한 것은 AI 도입 자체가 아니라, 성과를 위해 어디를 바꾸고 어디에 AI를 적용할 것인가입니다.

| Shot | TC | Visual | Source | Camera | Motion Graphic | Transition In | Transition Out | SFX |
|---|---|---|---|---|---|---|---|---|
| 1A | 0.0–2.0 | 다크 네이비 공간에 AXCORE Diamond가 점에서 생성, 1px Blue Line이 오른쪽으로 뻗음 | MG | 우측 Truck (Line 속도와 동기) | Diamond scale-in, Line draw-on, 미세 Orbit 링 1개 | Black → Navy (영상 시작) | Line이 수평으로 화면을 가로지르며 **Slit Mask**가 됨 | Node Activation (soft), Line |
| 1B | 2.0–5.2 | 사무실 엔지니어 실사, 공간에 데이터 Label이 원근으로 부착 (`생산 계획`, `재고 현황`, `품질 기록`) | V1 (K1) | V1 자체 우측 Dolly + 가상 카메라 우측 Pan 유지 | Planar-tracked Label 3개 + Leader Line, Diamond가 Label 사이를 이동 | 1A의 Line이 위아래로 열리는 Slit Mask Reveal | 카메라가 같은 속도로 우측 Pan 지속 → 다음 플레이트가 같은 수평 공간에서 진입 (경계는 1px Blue Seam) | UI Open (labels) |
| 1C | 5.2–8.4 | 공장 현장, 태블릿을 든 작업자가 좌→우 보행, 설비 위 `MES · 생산실적`, `설비 가동` Label | V2 | 작업자와 같은 방향·속도의 우측 Truck | Tracked Label 2개, 작업자 태블릿에 작은 UI 화면 합성 | Camera Direction Continuity (우측 Pan, Seam Line) | 태블릿 화면(흰 사각형)으로 Push-in → **Graphic Match** | Data Scan tick |
| 1D | 8.4–11.0 | Top-down 책상, 수기 점검표·스프레드시트·검사 문서. 각 문서에 Scan Bracket과 Label (`점검표 · 수기`, `생산일지 · Excel`, `검사성적서`) | V3 | Top-down 우측 Glide + 미세 Push | Corner Bracket Lock-on, 문서에서 데이터 점(Dot)이 떠오름 | 태블릿 흰 사각형이 화면을 채운 뒤 클립보드 종이로 축소 정합 (Match Cut) | 떠오른 Dot들이 카메라 쪽으로 다가오며 전경을 지나가고 그 뒤에 회의실이 드러남 (**Foreground Occlusion Wipe**) | Data Scan ×3 |
| 1E | 11.0–15.0 | 회의실 벽 디스플레이(Screen Replacement)에 수많은 업무 데이터 점, 하나의 Point가 Diamond로 선택됨 | V4 + UI | V4 자체 Push-in → 가상 카메라가 선택된 Point로 **Push-in** | Tracked Screen, Data Scatter, Diamond Cursor 착지, Ring Pulse, `AX Point` 라벨 | Dot Occlusion Wipe | 선택 Point 안으로 Push-in → 화면 콘텐츠의 네이비 배경이 곧 SCENE 02의 공간 | UI Selection, Camera Push |

핵심 메시지: 수많은 데이터 중 **어디(Point)**를 바꿀 것인가를 먼저 찾는다 → 이것이 `AXpoint` 이름과 연결된다.

---

## SCENE 02 — 15.0–31.0s · "업무를 이해하는 것부터"
Narration: 기업의 AI 전환은 업무를 이해하는 것부터 시작됩니다. 회사의 업무와 데이터를 분석해 DX와 AX가 필요한 영역을 찾아 진단에서 실행까지 하나의 흐름으로 설계합니다.

| Shot | TC | Visual | Source | Camera | Motion Graphic | Transition In | Transition Out | SFX |
|---|---|---|---|---|---|---|---|---|
| 2A | 15.0–17.0 | 네이비 공간 중앙 Diamond, Pull-out하며 깊이가 다른 데이터 Source 카드들이 드러남 | MG + 실사 Crop | Pull-out (zoom 3.0 → 1.0), 카드별 Parallax | 카드 7장이 Z-depth별로 배치 | 1E의 Push-in과 연속 (같은 Point) | Diamond가 첫 카드로 이동 | Camera Push (reverse) |
| 2B | 17.0–24.0 | Diamond가 Source를 하나씩 Scan/Identify: `문서 · 작업표준서`, `Excel · 재고현황`, `ERP · 수주`, `MES · 생산실적`, `설비 · 센서`, `수기 · 점검표`, `작업자 · 현장 업무` | MG + V2/V3/V5 Crop (카드 내부 실사 영상) | Diamond를 따라 우측 Pan | Scan Line Sweep, Bracket Lock, Type Label, 카드 → 중앙 Spine으로 **직교(Orthogonal) 연결선** | — | 연결선이 중앙 Spine으로 모임 | Data Scan ×7, Node Activation |
| 2C | 24.0–28.0 | 카드가 Chip으로 접히고 선을 따라 이동 → 하나의 Process Flow (`수주 → 설계 → 구매 → 생산 → 품질 → 출하`) | MG | 수평 정렬에 맞춰 Pull-back | Chip Flow, Process Node 정렬 | — | Flow의 6 Node가 중앙으로 수렴하며 선이 짧아짐 | Line Movement, Connector |
| 2D | 28.0–31.0 | Flow Line이 **AXpoint 검색바(Pill)**로 Morph, Pill 밖으로 흰 UI 공간이 확장 | MG → UI | 정지 → 미세 Push | Line → Pill Shape Morphing, Circular Mask 확장 (네이비 → 화이트) | — | 흰 공간 = AXpoint 랜딩 | Transition (soft swell), UI Open |

---

## SCENE 03 — 31.0–50.0s · AXpoint
Narration: AI 컨설턴트 AXpoint는 사내 문서와 데이터에서 실제 업무 흐름과 변화의 우선순위를 찾아냅니다. 필요한 기능은 워크스페이스에서 직접 선택해 우리 회사의 업무 환경에 맞게 구성합니다.

하나의 거대한 UI 캔버스(좌→우 6개 영역)를 하나의 카메라가 Pan / Push / Pull로 이동한다. 상단 Stepper(자료 올리기 · 자료 정리 · 진단 결과 · 개선 과제 · 로드맵 · 보고서)가 카메라와 함께 진행 상태를 표시한다.

| Shot | TC | Visual | Source | Camera | Motion Graphic / UI | Transition In | Transition Out | SFX |
|---|---|---|---|---|---|---|---|---|
| 3A | 31.0–33.2 | 랜딩 `제조 AX를 위한 AI 컨설턴트`, 검색바에 `데모기업` 타이핑 → `기업 찾기` 클릭 | UI | 미세 Push-in | 타이핑, Diamond Cursor 클릭, 버튼 Press | 2D Pill Morph | 확인 카드 → 우측 Pan | UI Selection, typing ticks |
| 3B | 33.2–36.4 | `현장 서류를 올려주세요` Upload, 파일 6개가 날아와 리스트로 정렬 (`3월 생산일지_v3.pdf` 등, IR p35 파일명) | UI | 우측 Pan → Upload 영역 Push-in | File Chip 비행(Motion Blur) → List 착지, Progress | 3A 버튼 클릭이 원인 | 리스트가 분류 컬럼으로 재배열 | UI Open, Chip land ×6 |
| 3C | 36.4–39.0 | `자료 분류`: 파일이 `생산 / 품질 / 영업 / 구매 / 설비 / 인사` 태그 컬럼으로 정렬, `총 48건 수집` | UI | 우측 Pan | Tag 부착, Count-up 0 → 48 | 리스트 재배열 (Object Continuity) | 컬럼이 진단 영역의 축(axis)으로 변환 | Node Activation |
| 3D | 39.0–42.2 | `AX 진단`: 5각 Radar + 5대 지수 Bar (34.1/56.3/45.0/47.2/25.0), `종합 41.52점 → Lv.2 데이터화·표준화` | UI | 우측 Pan + Push | Radar Draw-on, Bar Fill, Count-up | 분류 컬럼 → Radar 축 | 가장 낮은 `AI 활용 및 성과` Bar의 끝 Line이 오른쪽으로 늘어남 | Data Scan, UI tick |
| 3E | 42.2–45.0 | `워크플로우 분석`: Bar Line이 Workflow Path가 되고 업무 Node 생성, 빨간 `기록 공백` Node, Diamond 모양 `AX 지점` 마커 | UI | Line을 따라 우측 Truck | Score Line → Workflow Line **Morph**, Node Pop, 부서 Legend | Bar Line 연장 (Graphic Match) | 문제 Node Highlight → Card 생성 | Line Movement, Node ×n |
| 3F | 45.0–47.4 | `개선 과제 후보 22개`, 카드 그리드에서 2개 선택(Check) = 우선순위 | UI | 카드로 Push-in | Card Spawn from Node, Selection Fill | Node → Card (Cause & Effect) | 선택 카드가 Timeline으로 이동 | UI Selection ×2 |
| 3G | 47.4–50.0 | `실행 로드맵` 단계 1 데이터화·표준화 / 단계 2 품질 안정화 → `진단 결과 요약` 보고서 카드 (`Lv.2`, `+8.6점`) | UI | Pull-out으로 6단계 전체 공개 | Card → Timeline 배열, Report Slide-up | 카드 이동 | 계속 Pull-out | Connector, UI Open |

---

## SCENE 04 — 50.0–73.0s · Workspace · Connector · OCR · Ontology
Narration: AXCORE는 다양한 업무 환경을 하나로 연결합니다. ERP, MES, CRM과 같은 사내 시스템부터 협업, 커뮤니케이션 등 다양한 외부 SaaS까지 커넥터로 연결합니다. 업무 파일은 데이터로, 수기 정보는 OCR을 통해 연결합니다. AI가 설비, 자재, 공정, 제품, 사람과 업무의 관계를 이해하도록 만듭니다. 이것이 AXCORE Ontology입니다.

| Shot | TC | Visual | Source | Camera | Motion Graphic / UI | Transition In | Transition Out | SFX |
|---|---|---|---|---|---|---|---|---|
| 4A | 50.0–55.0 | 보고서의 `AI 워크스페이스` 배너로 Push-in → Workspace 기능 선택: `경영관리 · 제품설계 · 생산관리 · 장비관리 · 품질관리 · 재고·물류 · 영업관리 · 고객지원`, 5개 선택 → 사이드바 + 대시보드로 조립 | UI | Push-in → 정지 → 미세 Pull | Card Select, Fly-to-Layout, Dashboard Widget Build | 3G Pull-out 직후 배너로 Push (방향 반전은 클릭 행위로 동기) | Workspace가 축소되며 주변이 네이비로 | UI Selection ×5, UI Open |
| 4B | 55.0–60.0 | 네이비 공간 중앙 Workspace, 외곽에서 `ERP · MES · CRM` (사내 시스템), `Excel · 문서` (업무 파일), `협업 · 메신저 · 메일 SaaS`, `설비 · PLC` 블록이 진입, **Connector** Chip이 꽂히며 연결 | MG + UI | Pull-out (카드 Push-in의 역방향) | Block Slide-in, Connector Plug Snap, Data Pulse | 4A 축소 = Pull-out to Space | 문서 블록 쪽으로 Push | Connector ×6 |
| 4C | 60.0–64.0 | 수기 점검표(실사 K3 Crop)에 OCR Scan Beam → 인식 Box → 구조화 테이블. 이어서 `프레스3 / #3 Press / 3호기` → `EQ-PRS-03` 표준 코드로 수렴 (데이터 표준화) | MG + K3 | Push-in → 우측 Pan | Scan Beam, Field Box, Text → Table Row Fly, Label Merge | 문서 블록 Push | 표준 코드 Chip이 중앙으로 빨려들어감 | Data Scan (long), Node |
| 4D | 64.0–73.0 | 모든 연결선이 중앙 Diamond(Ontology Core)로 수렴 → 처음엔 복잡한 데이터 Cloud → 정리되어 6개 Entity `설비 · 자재 · 공정 · 제품 · 사람 · 업무` 와 관계(`수행 / 투입 / 생산 / 담당 / 관리 / 운전`) 형성 → `제품 불량 → 공정 → 설비 → 담당자` 경로가 Context로 하이라이트, `AXCORE Ontology` | MG | Pull-out + 느린 Orbit 회전 | Cloud → Structure Morph, Edge Draw, Relation Label, Path Traversal | 표준 코드 Chip 수렴 | 구조 전체가 축소되며 모니터 화면이 됨 | Node Activation ×6, Transition swell |

---

## SCENE 05 — 73.0–89.0s · AI Assistant
Narration: 이제 여러 시스템과 문서를 오갈 필요가 없습니다. 질문 하나면 AI가 관련 데이터를 찾아 현재 상황과 원인, 업무의 맥락까지 제시합니다.

| Shot | TC | Visual | Source | Camera | Motion Graphic / UI | Transition In | Transition Out | SFX |
|---|---|---|---|---|---|---|---|---|
| 5A | 73.0–76.0 | Ontology 구조가 축소되며 실사 엔지니어의 모니터 화면이 됨 → AI Assistant 입력창 | V7 (K7) | Pull-out (화면 밖으로 빠져나오며 실사 공간 공개) | Planar-tracked **Screen Replacement** | 4D 구조 = 모니터 콘텐츠 (Graphic Match) | 타이핑 | Camera Push (reverse) |
| 5B | 76.0–78.5 | 질문 입력 `이번 주 2라인 불량이 늘어난 원인은?` → 전송 | V7 + UI | V7 Push-in | Typing, Send | — | 화면에서 Line이 공간으로 뻗음 | typing, UI Selection |
| 5C | 78.5–84.0 | 모니터 뒤 공간에 Source 패널 5개(`ERP · MES · 문서 · 생산 데이터 · 품질 데이터`)가 원근으로 부착, Line이 Source를 따라 이동하며 항목 Highlight → 모니터로 회수 | V7 + MG | V7 Push-in, Panel Parallax | Environmental UI (homography tracked), Search Line Travel, Item Select | — | 선택 데이터가 화면으로 들어감 → 화면으로 Push-in | Data Scan ×5, Line |
| 5D | 84.0–89.0 | Answer Panel: `현재 상황 / 원인 / 맥락` 3단 구조 + 출처 Tag, 원인 섹션의 추세 Line | UI | 화면 안으로 Push-in, 원인 그래프의 Line으로 이동 | Section Reveal, Source Tag, Trend Line | Push-in | 추세 Line을 따라 우측으로 → 수요 예측 그래프 | UI Open ×3 |

---

## SCENE 06 — 89.0–106.0s · 분석에서 실행으로
Narration: 영업에서는 수요를 예측하고, 생산과 품질에서는 이상 징후를 감지합니다. 반복 업무를 자동화하고 설비와 로봇까지 연결하며, AI는 분석에서 실행으로 확장됩니다.

| Shot | TC | Visual | Source | Camera | Motion Graphic / UI | Transition In | Transition Out | SFX |
|---|---|---|---|---|---|---|---|---|
| 6A | 89.0–93.0 | `영업관리 · AI 수요 예측`: 실적(Solid) → 예측(Dashed + Band) | UI | Line을 따라 우측 Truck | Line Draw, Forecast Band | 5D 추세 Line 연속 | 예측 Line이 패널 밖으로 계속 진행 | Line Movement |
| 6B | 93.0–97.5 | 컨베이어 실사 위로 같은 Line이 벨트 원근을 따라 센서 신호가 됨 → Spike → 부품에 `이상 징후` Circle | V6 + MG | V6 우측 Truck과 Line 속도 동기 | Perspective Signal Line, Anomaly Ring | Line Graphic Match (UI → 실사) | Anomaly Circle 축소 → Workflow Node | Node Activation, alert tick |
| 6C | 97.5–101.5 | 반복 수작업 카드(엑셀 → 메일 → 엑셀)가 압축되어 자동 Workflow로: `이상 감지 → 조치 제안 → 작업 지시 → 자재 발주 → 알림 발송 → 추적 관리` | MG | 우측 Truck | Card Stack Compress, Sequential Node Check | Circle → Node (Shape Match) | 마지막 Node의 Line이 설비 제어 Line으로 | Connector ×6 (rhythmic) |
| 6D | 101.5–106.0 | 제어 패널 실사, HMI 화면에 `PRS-03 · 점검 필요` → 손이 버튼을 누르는 순간 `조치 실행 · 정상 운전` | V5 + UI | V5 Push-in | HMI Screen Replacement (tracked), Line Pulse into machine | Control Line 연속 | HMI 화면으로 Pull-out (다크 공간) | UI Selection (press), Node |

---

## SCENE 07 — 106.0–116.0s · 연결될수록
Narration: 업무와 데이터가 연결될수록 AI는 더 빠르게 이해하고 더 정확하게 판단합니다. 더 빠른 판단, 더 효율적인 실행. 더 높은 업무 생산성으로.

| Shot | TC | Visual | Source | Camera | Motion Graphic | Transition In | Transition Out | SFX |
|---|---|---|---|---|---|---|---|---|
| 7A | 106.0–109.0 | HMI 화면의 빛이 Node가 되고, Pull-out하면 `데이터 · 문서 · 시스템 · 워크스페이스 · 사람 · 설비` 6 Node와 중앙 Diamond의 간결한 Network | MG | Pull-out | Ring Network, Edge Pulse | HMI → Node (Graphic Match) | — | Transition swell |
| 7B | 109.0–116.0 | Pulse 속도가 점점 빨라지고 불필요한 선이 사라지며 핵심 Flow(Orbit)만 남음. Keyword `더 빠른 판단` → `더 효율적인 실행` → `더 높은 업무 생산성` | MG | 미세 Push-in | Pulse Acceleration, Edge Fade, Keyword Line Reveal | — | Orbit이 Diamond로 수렴 시작 | Node ticks accelerating |

---

## SCENE 08 — 116.0–120.0s · Logo
Narration: AI 전환의 가장 쉬운 시작. AXCORE

| Shot | TC | Visual | Source | Camera | Motion Graphic | Transition In | Transition Out | SFX |
|---|---|---|---|---|---|---|---|---|
| 8A | 116.0–117.4 | Line / Node / Orbit이 Diamond로 수렴 | MG | 정지 | Converge (폭발 없는 Calm Ease) | 7B Orbit | — | Logo Reveal (soft riser) |
| 8B | 117.4–118.6 | Diamond가 로고 내 실제 위치로 이동, Wordmark가 Diamond 기준 좌우 Mask Reveal | 로고 PNG (원본) | 정지 | Mask Wipe | — | — | Logo hit (soft) |
| 8C | 118.6–120.0 | `AI 전환의 가장 쉬운 시작.` | MG | 정지 | Line Reveal | — | End | BGM resolve |
