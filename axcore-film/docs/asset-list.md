# Asset List — AXCORE Preview v01

## 1. Live-action plates (AI generated)

모든 실사 플레이트는 Higgsfield MCP로 생성했다. 먼저 Nano Banana Pro(`nano_banana_pro`)로 키프레임 이미지를 만들고, 그 이미지를 시작 프레임으로 Kling 4.0(`kling4_0`, `image-to-video`)에 넣어 영상을 만들었다. 출력은 720p/24fps이며, 파이프라인에서 960×540으로 캐시하면서 색보정을 적용한다.
> 참고: 이미지 잡 메타데이터에는 모델이 `nano_banana_2`로 표시된다. 요청은 `nano_banana_pro`로 보냈다.

| ID | 키프레임 | 영상 | 내용 | 사용 장면 | 카메라 |
|---|---|---|---|---|---|
| K1/V1 | `K1_office_engineer.png` | `V1_office_engineer.mp4` | 사무실 엔지니어(정면) | S01-1B, S06 배경(블러) | 우측 Dolly + Push |
| K2/V2 | `K2_factory_floor.png` | `V2_factory_floor.mp4` | 공장, 종이 작업지시서를 든 작업자 | S01-1C, S02 카드, S04 배경(블러) | 우측 Truck |
| K3/V3 | `K3_documents_topdown.png` | `V3_documents_topdown.mp4` | 수기 점검표·문서 Top-down | S01-1D, S02 카드 | 우측 Glide |
| K4/V4 | `K4_meeting_room.png` | `V4_meeting_room.mp4` | 회의실 + 벽 디스플레이 | S01-1E, S03 배경(블러) | Push-in |
| K5/V5 | `K5_control_panel.png` | `V5_control_panel.mp4` | 프레스 제어 패널 + HMI | S02 카드, S06-6D | Push-in |
| K6/V6 | `K6_conveyor.png` | `V6_conveyor.mp4` | 컨베이어 + 검사 카메라 | S06-6B | 우측 Truck |
| K7/V7 | `K7_engineer_ots.png` | `V7_engineer_ots.mp4` | 어깨너머 모니터 샷 | 예비 플레이트 | Push-in |
| K8/V8 | `K8_engineer_wide.png` | `V8_engineer_wide.mp4` (8s) | 같은 인물의 와이드 샷, 창 공간 | S05 | Dolly-in |

폐기한 플레이트(`*_rejected.*`)
- K7 v1: 모니터 뒷면만 보여서 Screen Replacement가 불가능했다.
- K2/V2 v1: 태블릿이 등장했다. 웹 기반 서비스이므로 태블릿·휴대폰 장면은 제외한다.

## 2. Client-supplied
| 파일 | 용도 |
|---|---|
| `assets/logo/AXCORE_logo_w2.png` | 로고. Diamond 위치·크기·색(#0053FC)을 이 파일에서 직접 추출했다. 워드마크와 블루 바를 레이어로 분리해 Reveal에 사용한다. |
| `assets/ui/axpoint_UI_capture.webp` | AXpoint UI의 Source of Truth. `src/compositing/ui_axpoint.py`에서 벡터로 재구성했다. |
| `assets/source/client/ontology_scene_prev.mp4` | 이전 작업에서 만든 온톨로지 장면. S04 64.2–73s와 S05 모니터 화면에 원본 그대로 사용한다. 2.39:1 레터박스는 같은 영상의 블러 이미지로 채운다. |
| `assets/source/reference/*` | IR Deck, 레퍼런스4·5. 분석용이며 영상에는 사용하지 않는다. *(git 제외)* |

## 3. Typography
- Pretendard Regular / Medium / SemiBold / Bold (OFL). 자간은 0이다.
- Nanum Pen Script (OFL): 손글씨 기록을 묘사하는 OCR 원본에만 사용한다.

## 4. Graphics / UI (code-generated)
- `gfx.py`: Diamond(로고 심볼), Line·Orbit·Node·Bracket·Ripple, 카드·칩, chamfer 카드, 토글
- `ui_axpoint.py`
  - AXpoint: 랜딩/검색, 업로드 리스트, 자료 분류, 레이더 + 5대 지수, 워크플로우, 개선 과제 카드, 로드맵, 보고서
  - 워크스페이스: 사이드바와 위젯
- `background.py`: Navy space(bloom), White UI space, Defocused orbit field
- 화면 숫자는 IR Deck 데모 값만 사용한다: 34.1 / 56.3 / 45.0 / 47.2 / 25.0, 41.52, Lv.2, 22 / 3 / 5, +8.6, 48. 그 외 예시 데이터에는 `DEMO` 라벨을 붙였다.

## 5. Sound (code-generated, no samples)
- `src/audio/bgm.py`: 100 BPM, Dm9–B♭maj7–Fmaj7–C(add9). Pad → Arp(15s~) → Bass(31s~) → Kick(73s~) / Hat(89s~) 순으로 레이어를 쌓고, 113s Riser를 거쳐 117s Fmaj9로 해결한다.
- `src/audio/sfx.py`: node, ui_tick, select, scan, connector, line, push/pull, data_rise, alert, merge, logo 등. 각 장면 모듈의 `SFX` 큐(총 220여 개)에서 자동 배치된다.
- Stems: `renders/stems/bgm_stem.flac`, `sfx_stem.flac`, `master_mix.flac`
- BGM은 약 −26 dB RMS, Master peak는 −3 dBFS 이하로 맞춰 나레이션 Headroom을 확보했다.
