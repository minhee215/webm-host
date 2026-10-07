# AXCORE 서비스 홍보영상 — 기획 · 프롬프트 · 제작 구조

- 길이 109.5초 / 1920×1080 / 24fps / H.264 + AAC
- 레퍼런스: SK AX 홍보영상(실사 → 시안 라이트 스트릭 → 화이트 도트그리드 콜라주 → 네이비 블록 → 데이터 UI → 로고)
- 나레이션: `assets/narration.mp3` (AXCORE_v4), 0.8초 프리롤 뒤에 시작
- 모든 장면 플레이트는 Higgsfield MCP의 **Nano Banana Pro**로 생성(21장, `assets/plates.json`)
- 모션그래픽·합성·전환·마감은 전부 Python(skia-python + numpy)으로 렌더링(`render.py`)

## 1. 나레이션 타이밍 측정
대본 32문장을 나레이션의 무음 구간(−35dB, 0.18초 이상)과 음절 수에 맞춰 동적계획법으로 정렬했습니다.
정렬 결과는 `scenes.py`의 `CUE` 표에 있으며 모든 그래픽 등장이 이 큐에 맞춰 움직입니다.
(예: "ERP·MES·CRM"과 "설비·자재·공정·제품·사람"은 단어 단위로 카드가 하나씩 등장)

## 2. 스토리보드 (영상 시간 기준)

| # | 시간 | 나레이션 | 화면 | 전환 |
|---|------|----------|------|------|
| 01 | 0.0–4.6 | AI가 기업의 일하는 방식을… | 새벽 도심 항공 와이드, 슬로 푸시인, 시안 라이트 스트릭이 도시를 가로지름 | 페이드 인 |
| 02 | 4.6–8.0 | 하지만 중요한 것은 AI 도입 자체가 아니라 | 초고층 로우앵글, 롤 회전 드리프트 + 대각선 스트릭 | 라이트 스트릭 와이프 |
| 03 | 8.0–13.1 | 어디를 바꾸고 어디에 AI를 적용할 것인가 | 정면 파사드 그리드: 흰 브래킷이 여러 창을 탐색 → 불 켜진 회의실에 시안 프레임 고정, 시안 라인이 파사드 전체로 확장(레퍼런스 7번 컷 문법) | 줌스루 |
| 04 | 13.1–17.3 | 기업의 AI 전환은 업무를 이해하는 것부터 | 회의 테이블 탑뷰(얼굴 없음), 스캔 라인 → 문서별 브래킷·칩 → 문서 간 연결선(업무 흐름 이해) | 화면 전체가 콜라주 타일로 축소 |
| 05 | 17.3–25.8 | 업무와 데이터 분석 → DX·AX 영역 → 진단부터 실행까지 | 화이트 도트그리드 2.5D 콜라주(8개 업무 사진·라벨·네이비 스퀘어), 스캔 → DX(네이비)/AX(브랜드 블루) 배지, 비대상은 디밍 → 타일이 Diagnose→Analyze→Design→Execute 흐름 카드로 정렬, 펄스 이동, Diagnose 카드로 푸시인 | 카드 확장 |
| 07 | 25.8–28.4 | AI 컨설턴트 AXpoint는 | 문서를 검토하는 손(실사) + 글래스 카드 "AXpoint · AI Consultant", 종이 위 텍스트 줄 하이라이트(트래킹) | 디졸브 + 라이트 리크 |
| 08 | 28.4–33.9 | 사내 문서·데이터에서 업무 흐름과 우선순위 | 딥네이비 데이터 공간: 문서 카드가 날아와 워크플로 노드로 흡수 → 우선순위 카드 3→2→1 순 등장(히어로 1위가 마지막, 시안 엣지 글로우) | 라이트 스트릭 |
| 09 | 33.9–40.6 | M-AI Works에서 기능 선택 → 워크스페이스 구성 | **[추가 요청: 기업]** 손을 든 인물(뒷모습) 주위로 8개 모듈이 떠 있고, 5개가 워크스페이스 슬롯으로 끌려와 추가(+), Robot Link는 제거(−)되고 Chat Q&A가 추가 → 글래스 패널이 솔리드 화이트 UI로 전환되며 위젯 활성화 | 줌스루 |
| 10 | 40.6–44.6 | AXCORE는 다양한 업무 환경을 하나로 연결 | 화이트 도트그리드, AXCORE 로고 조립(회색 글리프 와이프 → 블루 다이아 → 블루 바 순차), 6개 현장 사진 타일이 네이비 라인과 스퀘어 노드로 로고에 연결, 블루 펄스 | 네이비 블록 모자이크 |
| 11 | 44.6–48.8 | ERP·MES·CRM 사내 시스템 | 데이터센터 복도 돌리 인, 단어 큐마다 다크 글래스 카드 등장 → 시안 커넥터가 AXCORE 코어 노드로 연결, SCM·PLM·QMS 등 보조 칩 | 라이트 스트릭 |
| 12 | 48.8–53.6 | Gmail·Slack·Notion 외부 SaaS 커넥터 | **[추가 요청: 개인]** 태블릿 탑뷰, 손가락이 외부 플랫폼 칩을 끌어당겨 화면 안 "Connectors" 목록에 도킹(원근 매핑), 체크 표시, Drive·Calendar 등 선택지 부유 | 줌스루 |
| 13 | 53.6–58.2 | 업무 파일은 데이터로, 수기 정보는 OCR로 | 파일 카드(XLSX·PDF·DOCX·CSV)가 구조화 데이터 테이블로 변환 / 클립보드 손글씨에 OCR 스캔 → 기울어진 박스 → 추출 텍스트 칩 | 디졸브 |
| 14 | 58.2–68.1 | 설비·자재·공정·제품·사람과 업무의 관계 → AXCORE Ontology | **[추가 요청: 온톨로지 강조]** 2.5D 그래프: 바닥에 업무의 START→END 흐름(Order→Plan→Procure→Produce→Inspect→Deliver), 단어 큐마다 엔티티 등장 + 관계선, 시안 펄스가 시작에서 끝까지 흐르며 연결된 엔티티가 점등(맥락 이해) → 카메라 풀백·상승 오빗, "AXCORE Ontology" 타이틀 | 줌스루 |
| 15 | 68.1–71.8 | 여러 시스템과 문서를 오갈 필요가 없습니다 | 모니터 앞 인물(뒷모습) 위로 9개 앱 창이 흩어져 등장 → 하나로 모여 AXCORE 질문창 | 창이 확장되어 다음 장면 |
| 16 | 71.8–78.7 | 질문 하나면 → 상황·원인·맥락 제시 | **[추가 요청: Q&A + 온톨로지]** 화이트 워크스페이스 UI: 질문 타이핑 → 오른쪽 "Ontology trace"에서 Line 3 → Product → Welding → Robot → Material Lot → Maintenance 순으로 경로 탐색, 데이터 소스 칩 → 답변 카드(현재 상황/원인/맥락)가 해당 노드를 하이라이트하며 생성 | 휩 팬 |
| 17 | 78.7–80.9 | 영업에서는 수요를 예측하고 | 리테일 통로 돌리 + 글래스 예측 차트(실적선 → 점선 예측 + 신뢰구간) | 휩 팬 |
| 18 | 80.9–84.3 | 생산·품질 이상 징후 감지 | 생산라인 제품에 트래킹 박스, 한 개가 ANOMALY로 전환·펄스, 진동 신호 카드의 스파이크 감지 | 디졸브 |
| 19 | 84.3–88.1 | 반복 업무 자동화, 설비·로봇 연결 | 반복 업무 카드에 AUTO-RUN 진행·체크 → 시안 커넥터가 로봇 그리퍼로 연결, 레티클 | 줌스루 |
| 20 | 88.1–91.3 | 분석에서 실행으로 확장 | 스마트팩토리 하이앵글, 노드 네트워크가 셀 단위로 확산, Analyze→Execute 토글 | 디졸브 + 리크 |
| 21 | 91.3–97.4 | 연결될수록 더 빠르게 이해, 더 정확하게 판단 | 블루아워 도시·산업단지 항공, 노드가 늘어나며 허브로 정리되는 네트워크 | 라이트 스트릭 |
| 22 | 97.4–102.5 | 더 빠른 판단 / 더 효율적인 실행 / 더 높은 생산성 | 태블릿을 든 손 → 창고 돌리 → 걸어가는 팀(뒷모습), 비트마다 스트릭 | 휩 팬 ×2 |
| 23 | 102.5–109.5 | AI 전환의 가장 쉬운 시작. AXCORE | 화이트 도트그리드, 네이비 라인·스퀘어가 중앙으로 수렴, 프레임 브래킷 → "AXCORE" 발음에 맞춰 블루 바가 순차 정착, 글린트, 웜화이트 페이드 | 네이비 블록 모자이크 |

## 3. 프롬프트 설계 (Nano Banana Pro)
첨부된 프롬프트 작성법의 구조(팔레트를 잠그고, 히어로 하나만 강조색, 구성·조명·질감·회피 항목을 분리)를
이 프로젝트의 코퍼레이트 톤으로 옮겨 모든 플레이트에 같은 섹션 순서를 썼습니다.

```
SUBJECT: 무엇을, 어디서 (얼굴 비노출 · 손/뒷모습)
COMPOSITION: 카메라 위치, 히어로 위치, 그래픽용 여백
PALETTE: natural industrial neutrals / steel gray / deep navy / warm white / blue·indigo, cyan은 통제된 포인트
LIGHT: soft daylight & practical (실사) · soft studio (데이터 장면) · edge lighting · localized glow
FINISH: premium grounded corporate film still, photorealistic, fine film grain
AVOID: text, logos, faces, neon overload, holograms, sci-fi clutter
```

예) 09_handraise
> SUBJECT: over-the-shoulder view from behind of a business professional in a navy blazer standing in a bright warm white modern office, right hand raised in mid-air at the right third of the frame as if arranging invisible floating panels, face not visible. COMPOSITION: large empty bright space in the center of the frame in front of the hand for floating interface overlays… PALETTE: warm white walls, light oak, steel gray, navy blazer, subtle blue accents. LIGHT: soft daylight from large windows, gentle bloom. FINISH: premium corporate film still, photorealistic, shallow depth of field, fine grain. AVOID: faces, text, logos, screens with content.

| 플레이트 | 용도 |
|---|---|
| 01_skyline · 02_tower · 03_facade | 오프닝(도시 → 타워 → 파사드 창 선택) |
| 04_table · 07_docs · 12_handwritten | 업무 이해 · AXpoint · OCR |
| 05_warehouse · 06_line · 16_retail · 17_robot · 18_factory | 현장 · 예측 · 이상감지 · 자동화 |
| 08_navycards · 10_datacenter · 13_navystage | 데이터 공간 · 사내 시스템 · 온톨로지 무대 |
| 09_handraise · 11_tablet · 14_monitors · 15_whitedesk | 모듈 추가/제거 · 개인 커넥터 · 여러 시스템 · Q&A 배경 |
| 19_aerial · 20_team · 21_tablet_hold | 연결 네트워크 · 클로징 비트 |

## 4. 모션 · 마감 원칙 (프롬프트 작성법 반영)
- **히어로 1개 원칙**: 한 화면에서 강조색(밝은 장면은 AXCORE 블루 `#0054FE`, 어두운 장면은 시안 `#3CD3FF`)은 한 요소만 가짐(예: 우선순위 1위, AX 배지, Root cause 카드, 로고의 블루 파트).
- **2.5D 카메라**: 모든 플레이트가 멈추지 않는 드리프트(푸시인·롤·패럴랙스)를 갖고, 전환 중에도 계속 움직임. 비트에는 히어로로 착지하는 결정적 푸시인.
- **등장 문법**: ease-out expo + 작은 오버슈트 후 안착, 다중 요소는 스태거, 히어로는 마지막.
- **프레임 케이던스**: 등장 순간의 앞 40%만 12fps 스텝(스톱모션 스냅), 이후와 카메라·다이어그램은 24fps 풀프레임.
- **블러 분리**: 피사계 심도(플레이트 디포커스)와 속도 블러(휩 팬의 수평 방향 블러)를 별도로 처리.
- **마감**: 가장자리 한정 색수차, 포커싱 비네트(밝은 UI 장면에서는 자동 완화), 섀도·미드톤에만 걸리는 그레인(화이트 UI와 하이라이트는 깨끗하게), 라이트 리크는 전환에서만.
- **글래스모피즘 UI**: 백드롭 블러 + 틴트 + 상단 스펙큘러 + 헤어라인 보더 + 접지 그림자, 필요 시 엣지 글로우. 장면 09·15·16에서 반투명 카드가 솔리드 화이트 UI로 이어짐.
- **재현성**: `--seed`, `--chaos`(0~1) 하나로 지터·스태거·창 회전 등 랜덤 요소 전체를 제어. 같은 seed+chaos는 항상 같은 프레임.

## 5. 사운드
- 나레이션(AXCORE_v4) + 합성 음악 베드(D장조 Dmaj9–Bm11–Gmaj7–Asus, 92BPM: 패드·플럭 아르페지오·서브·셰이커)
- 전환마다 필터 노이즈 우시, 단어 큐마다 작은 틱, 로고에 임팩트
- 나레이션 기준 사이드체인 덕킹, 피크 −1dBFS

## 6. 실행
```
pip install skia-python scipy numpy pillow
python3 fetch_plates.py            # Nano Banana Pro 플레이트 다운로드 → plates/
python3 render.py                  # out/axcore_promo.mp4 (오디오 포함)
python3 render.py --stills 10,60   # 검수용 스틸
python3 render.py --range 58 68    # 구간 렌더
python3 render.py --seed new --chaos 0.5 --webm
```
