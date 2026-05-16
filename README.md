# C++ Machine Vision Inspection System POC

C++ OpenCV 기반의 표면 결함 검사 엔진입니다.
자동차 도장면/금속/플라스틱 표면 이미지를 입력받아 전처리, 룰베이스 결함 검출, 결함 측정, OK/NG 판정, 결과 리포트 생성을 수행합니다.
Python은 UI 및 장비 시뮬레이터 용도로만 사용하고, 핵심 검사 로직은 C++로 구현했습니다.

---

## 1. 프로젝트 개요

- **프로젝트명**: `machine-vision-inspection-poc`
- **포지셔닝**: 자동차 도장면/금속/플라스틱 표면을 가정한 룰베이스 머신비전 검사 POC
- **검사 대상 결함**: 스크래치, 얼룩, 이물(점 결함), 혼합 결함
- **출력**: OK / NG 판정, 결함 면적/길이/개수, 결함 시각화 PNG, JSON 리포트, 누적 CSV
- **장비 흐름 재현**: PLC trigger → Camera capture → C++ Vision → PLC result → Robot move

핵심 차별점은 **검사 로직이 Python ML 데모가 아니라 C++ OpenCV로 구현되어 있다는 점**입니다.
Streamlit UI와 시뮬레이터는 라인 PC 측 SW 동작을 재현하기 위한 보조 레이어입니다.

## 2. 지원 직무 연관성

본 프로젝트는 **머신비전 검사 설비의 소프트웨어 구조를 재현한 POC**이며, 룰베이스 영상처리, 검사 판정, UI, 장비 인터페이스 시퀀스를 포함합니다.

| 채용 직무 요구 | 본 프로젝트 대응 |
| --- | --- |
| 머신비전 시스템 구축 프로젝트 경험 | C++ OpenCV 엔진 + Camera/PLC/Robot 시뮬레이터 + Streamlit UI 일체 구축 |
| 로보틱스 영상처리 알고리즘 개발 경험 | C++ 전처리 → contour → 측정 → 판정 파이프라인 직접 설계 |
| 카메라/로봇/PLC 인터페이스 개발 경험 | `interface/` 시뮬레이터 + `SequenceController` 오케스트레이션 |
| 비전 시험 및 CS 경험 | pytest CLI 통합 테스트, 합성 케이스 별 기대 판정 정의 |
| 2D/3D 광학계 및 조명 테스트 | `docs/camera_lighting_note.md`에 조명 영향 / 한계 명시 |
| 룰베이스 영상처리 알고리즘 개발 | OK/NG 판정 룰을 코드/문서에 명문화 |
| 검사 기능 설계/개발 | `InspectionEngine` 단일 진입점 설계, 측정/판정 분리 |
| UI 포함 | Streamlit UI에서 C++ CLI 호출, 결함 테이블/메트릭 시각화 |
| C++, C# 우대 | C++17 + CMake 빌드 구조, 동일 CLI를 C# HMI로 호출 가능 |

## 3. 기존 C++ 경력과 머신비전 직무 연결

기존 경로탐색 및 HD Map 기반 자율주행 관련 개발을 C++ 중심으로 수행하며 대용량 공간 데이터 처리, 판단 로직 설계, 성능을 고려한 시스템 개발 경험을 쌓았습니다. 이 경험을 머신비전 도메인으로 확장하기 위해 C++ OpenCV 기반 표면 결함 검사 엔진을 구현했습니다.

| 자율주행 / HD Map 경험 | 본 프로젝트로의 매핑 |
| --- | --- |
| 대용량 지도 데이터 타일 처리 | OpenCV `cv::Mat` 단위 픽셀 파이프라인 처리, stateless 엔진 설계 |
| 코스트맵 기반 판단 로직 | “면적·길이·개수” 3축 룰 기반 OK/NG 판단 |
| 경로 결과 검증 (룰 위반 체크) | 결함 측정값 → `verdict()` 단일 함수에서 룰 위반 검사 |
| 성능 고려 시스템 설계 | CLI 단일 바이너리화, subprocess 호출, 멀티스레드 확장 여지 확보 |
| 로그/리포트 시스템 | 결함 JSON + 누적 CSV로 검사 트레이스 보존 |

## 4. 시스템 아키텍처

```
PLC ─trigger─► Camera ─image─► C++ vision_inspector ─JSON/PNG/CSV─► UI / PLC / Robot
```

자세한 다이어그램은 [`docs/architecture.md`](docs/architecture.md) 참고.

## 5. 검사 알고리즘 흐름

```
Image → Gray → CLAHE → GaussianBlur → (Otsu | Canny) → close/open
      → findContours → 노이즈 필터 → bbox/center/length 측정
      → mm 변환 → verdict(OK/NG)
```

자세한 단계별 설명은 [`docs/inspection_algorithm.md`](docs/inspection_algorithm.md) 참고.

## 6. C++ 검사 엔진 설계

```
InspectionEngine ─┬─► Preprocessor      (전처리)
                  ├─► DefectDetector    (contour + 노이즈 필터)
                  ├─► Measurement       (bbox / center / length / mm 변환)
                  └─► ReportWriter      (PNG / JSON / CSV)
```

- C++17, OpenCV (core / imgproc / imgcodecs), CMake 3.14
- 외부 JSON 라이브러리 없이 직접 작성한 `ReportWriter::saveJsonReport`
- 자세한 설계 의도는 [`docs/cpp_design.md`](docs/cpp_design.md) 참고.

## 7. 장비 시퀀스

```
[PLC] trigger_on
[CAMERA] capture_frame image=sample_01.png
[VISION] inspection_started
[VISION] defect_count=2 result=NG
[PLC] write_result result=NG
[ROBOT] move_next_position position=UNLOAD
```

자세한 시퀀스는 [`docs/equipment_sequence.md`](docs/equipment_sequence.md) 참고.

## 8. UI 실행 방법

```bash
streamlit run app/streamlit_app.py
```

- 좌측 사이드바: 이미지 업로드 / 샘플 선택 / 파라미터 조정 / 검사 시작 버튼
- 메인: 원본 vs 결과 이미지 / 큰 OK·NG 배너 / 결함 메트릭 / 결함 리스트 / 검사 로그
- `vision_inspector` 바이너리가 없으면 빌드 안내 메시지가 사이드바에 표시됩니다.

## 9. CLI 실행 방법

```bash
./build/vision_inspector \
    --image data/sample_images/scratch_surface.png \
    --output data/results
```

전체 옵션:

```text
--image                  <image_path>           (required)
--output                 <output_dir>           default: data/results
--pixel-to-mm            <double>               default: 0.05
--max-defect-count       <int>                  default: 3
--max-defect-area-mm2    <double>               default: 2.0
--max-defect-length-mm   <double>               default: 5.0
--min-contour-area-px    <int>                  default: 30
```

Python wrapper로도 호출 가능합니다:

```bash
python scripts/run_cpp_inspector.py \
    --image data/sample_images/scratch_surface.png \
    --output data/results
```

## 10. 샘플 이미지 생성 방법

```bash
python scripts/generate_sample_images.py
```

생성 파일:

- `normal_surface.png` — 기본 설정에서 **OK** 기대
- `scratch_surface.png` — 길이 초과로 **NG**
- `dot_defect_surface.png` — 개수 초과로 **NG**
- `stain_surface.png` — 면적 초과로 **NG**
- `mixed_defects_surface.png` — 혼합 결함, **NG**

## 11. 테스트 방법

```bash
pytest -v
```

- Python 시뮬레이터/시퀀스/샘플 생성기는 항상 실행됩니다.
- C++ CLI 통합 테스트(`tests/test_cpp_cli.py`)는 `vision_inspector` 바이너리가 없으면 자동 skip합니다.

자세한 테스트 매트릭스는 [`docs/test_report.md`](docs/test_report.md) 참고.

## 12. 검사 결과 예시

검사를 1회 실행하면 다음 파일이 생성됩니다.

```
data/results/
  result_scratch_surface.png            # 결함 bbox + 판정 배너 오버레이
  inspection_report_scratch_surface.json # 결함별 상세 (defect_id, bbox, center, area, length…)
  inspection_results.csv                 # 1행 = 1회 검사, append-only 누적 로그
```

JSON 예시 (요약):

```json
{
  "image_name": "scratch_surface",
  "result": "NG",
  "defect_count": 1,
  "max_area_mm2": 0.9512,
  "max_length_mm": 26.83,
  "total_area_mm2": 0.9512,
  "created_at": "2026-05-16T09:30:01",
  "defects": [
    {
      "defect_id": 1,
      "bbox": {"x": 76, "y": 152, "w": 365, "h": 232},
      "center": {"x": 256.3, "y": 268.2},
      "area_px": 380.5,
      "area_mm2": 0.9512,
      "length_px": 536.5,
      "length_mm": 26.83
    }
  ]
}
```

## 13. 디렉토리 구조

```
machine-vision-inspection-poc/
├── README.md
├── requirements.txt
├── .gitignore
├── docs/                     # 아키텍처 / 알고리즘 / 시퀀스 / 광학 노트 / 테스트 리포트
├── cpp/                      # C++ 검사 엔진 (CMake 빌드)
│   ├── CMakeLists.txt
│   ├── include/              # 헤더 (Engine / Preprocessor / Detector / Measurement / ReportWriter ...)
│   └── src/                  # 구현 + main.cpp
├── app/streamlit_app.py      # Streamlit UI (C++ CLI 호출)
├── interface/                # PLC / Camera / Robot 시뮬레이터 + 시퀀스 컨트롤러
├── scripts/                  # 샘플 이미지 합성, C++ CLI Python wrapper
├── data/                     # sample_images/ , results/  (gitignored)
└── tests/                    # pytest 단위/통합 테스트
```

## 14. 기술 스택

- **C++17**, **OpenCV 4.x**, **CMake 3.14+**
- **Python 3.9+** (3.8도 동작), `streamlit`, `opencv-python`, `numpy`, `pandas`, `matplotlib`, `pytest`, `pillow`
- 빌드 / 실행: macOS, Ubuntu, Windows (CMake 표준 흐름)

## 15. 한계점

- 실제 광학계 / 조명 / 카메라 캘리브레이션이 적용되지 않은 합성 이미지 기반 POC입니다.
- 룰베이스 검사만 다루며 학습 기반 결함 분류(예: CNN segmentation)는 다루지 않습니다.
- PLC / Robot 인터페이스가 실제 산업 통신 프로토콜이 아닌 Python in-memory 시뮬레이터입니다.
- C++ 측 단위 테스트 프레임워크(GoogleTest)는 도입하지 않았으며 CLI 통합 테스트로 회귀를 잡습니다.

## 16. 개선 방향

- 실 데이터셋으로 알고리즘 임계값 / morphology 커널 재튜닝
- Pylon / Spinnaker / Vimba SDK를 사용하는 Camera 어댑터 추가 (`CameraSimulator` 대체)
- PyModbus / open62541 기반 PLC 어댑터, UR/ABB RTDE Robot 어댑터 추가
- 결함 분류기(예: CNN) 추가 시 본 룰베이스 결과를 1차 필터로 두는 cascade 구조
- C# WinForms HMI 추가 (동일 C++ CLI 재사용)
- GoogleTest 도입으로 `Measurement::pxToMm`, `verdict()` 등 unit-level 회귀 강화
- 멀티스레드 인스펙션 큐 (`InspectionEngine` stateless 설계 활용)

---

## 환경 준비

### Python 환경

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### OpenCV / CMake 설치

**macOS (Homebrew)**

```bash
brew install cmake opencv
```

**Ubuntu**

```bash
sudo apt-get update
sudo apt-get install -y cmake g++ libopencv-dev
```

**Windows**

- `vcpkg install opencv` 또는 OpenCV 공식 prebuilt 배포본 사용
- CMake에 `-DOpenCV_DIR=<path-to-opencv>/build` 추가

### C++ 빌드

```bash
cmake -S cpp -B build
cmake --build build
```

빌드 결과 실행 파일은 프로젝트 루트의 `build/vision_inspector` (Windows에서는 `build/Debug/vision_inspector.exe` 또는 `build/Release/vision_inspector.exe`)에 생성됩니다.
`scripts/run_cpp_inspector.py`가 이 세 경로를 모두 자동 탐색하므로 Streamlit UI / 시퀀스 컨트롤러 / 테스트는 별도 설정 없이 동작합니다.

### 전체 시퀀스 1회 실행

```bash
python -m interface.sequence_controller \
    --image data/sample_images/scratch_surface.png
```

PLC → Camera → C++ Vision → PLC → Robot 로그가 stdout에 출력됩니다.

---

## GitHub로 게시하기

```bash
git add .
git commit -m "Initial C++ machine vision inspection POC"

# 새 원격 레포 생성 (gh CLI 인증이 되어 있는 경우)
gh repo create machine-vision-inspection-poc --public --source=. --remote=origin --push
```
