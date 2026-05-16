# C++ Machine Vision Inspection System POC

[![CI](https://github.com/sungpyo9053/machine-vision-inspection-poc/actions/workflows/ci.yml/badge.svg)](https://github.com/sungpyo9053/machine-vision-inspection-poc/actions/workflows/ci.yml)

C++ OpenCV 기반의 표면 결함 검사 엔진입니다.
자동차 도장면/금속/플라스틱 표면 이미지를 입력받아 전처리, 룰베이스 결함 검출, 결함 측정, OK/NG 판정, 결과 리포트 생성을 수행합니다.
Python은 UI 및 장비 시뮬레이터 용도로만 사용하고, 핵심 검사 로직은 C++로 구현했습니다.

추가로 포함된 것:
- 실데이터 평가 하네스 (`scripts/evaluate_dataset.py` + 혼동행렬)
- C# WinForms HMI (`csharp_hmi/`, 동일 `vision_inspector.exe` 호출)
- 실 **Modbus TCP** PLC 어댑터 (`interface/plc_modbus.py`, pymodbus 기반)
- C++ 성능 **벤치마크 모드** (`--benchmark N`) + Python 일괄 측정 스크립트
- **GoogleTest** 기반 C++ 유닛 테스트
- 3D **stereo + disparity** mini-demo (`scripts/stereo_demo.py`)

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
| 머신비전시스템 구축 프로젝트 경험 | C++ OpenCV 엔진 + Camera/PLC/Robot 시뮬레이터 + Streamlit UI + C# WinForms HMI |
| 로보틱스 영상처리 알고리즘 개발 경험 | C++ 전처리 → contour → 측정 → 판정 파이프라인 + GoogleTest 단위 테스트 |
| 카메라/로봇/PLC 인터페이스 개발 경험 | Python 시뮬레이터 + **실 Modbus TCP 어댑터(pymodbus)** + `SequenceController` |
| 비전 시험 및 CS 경험 | pytest 단위/통합 + C++ GoogleTest + **데이터셋 평가 하네스(confusion matrix)** |
| 2D/3D 광학계 및 조명 테스트 | CLAHE / adaptive threshold 선택 사유 문서화 + **stereo disparity 3D mini-demo** |
| 룰베이스 영상처리 알고리즘 개발 | OK/NG 판정 룰을 코드/문서/단위 테스트에 명문화 |
| 검사 기능 설계/개발 | `InspectionEngine` 단일 진입점 + stateless 분리 + `--benchmark N` 성능 측정 |
| UI 포함 | Streamlit UI **+ C# WinForms HMI** 두 가지 (둘 다 동일 C++ CLI 호출) |
| C++, C# 우대 | C++17 + CMake + GoogleTest, .NET 8 WinForms HMI |

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

scratch_surface.png 검사 결과 화면:

![streamlit-ui](docs/images/streamlit_ui_result.png)

- 좌측 사이드바: 이미지 업로드 / 샘플 선택 / 파라미터 조정 / 검사 시작 버튼
- 메인: 원본 vs 결과 이미지 / 큰 OK·NG 배너 / 결함 메트릭 (개수·최대 면적·최대 길이·총 면적) / 결함 리스트 테이블 / 검사 로그
- `vision_inspector` 바이너리가 없으면 빌드 안내 메시지가 사이드바에 표시됩니다.
- 위 스크린샷은 `scripts/capture_ui_screenshot.py` 로 재현 가능 (Playwright 사용).

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

### Python 측 (항상 실행 가능)

```bash
pytest -v
```

- 시뮬레이터 / 시퀀스 / 샘플 생성기 / 데이터셋 평가 하네스 / Modbus 어댑터 / stereo 데모는 항상 실행됩니다.
- `tests/test_cpp_cli.py`, `tests/test_eval_harness.py::test_end_to_end_eval`는 `vision_inspector` 바이너리가 없으면 자동 skip합니다.

### C++ GoogleTest 측 (CMake 빌드 후)

```bash
cmake -S cpp -B build -DVISION_INSPECTOR_BUILD_TESTS=ON
cmake --build build
ctest --test-dir build --output-on-failure
```

GoogleTest는 CMake `FetchContent`로 자동 다운로드됩니다.
`Measurement::pxToMm`, `InspectionEngine::verdict`, `ReportWriter::saveJsonReport`, `ReportWriter::appendCsv` 등 핵심 함수가 단위 테스트로 회귀 보호됩니다.

### 실데이터셋 평가 (선택)

```bash
python scripts/generate_eval_dataset.py --out data/eval --count 40
python scripts/evaluate_dataset.py --dataset data/eval --out data/eval_runs
```

`data/eval_runs/confusion_matrix.csv`, `summary.json`이 생성됩니다.
MVTec-AD / KolektorSDD2 / Severstal로 교체 절차는 [`docs/dataset_evaluation.md`](docs/dataset_evaluation.md) 참고.

### 성능 벤치마크

```bash
python scripts/benchmark_inspector.py --images data/sample_images --runs 50
```

`data/benchmark_runs/benchmark.md` (Markdown 표) + `benchmark.csv`가 생성됩니다.

자세한 테스트 매트릭스는 [`docs/test_report.md`](docs/test_report.md) 참고.

## 12. 검사 결과 예시

### 12.1 시각 결과 (default 임계)

512×512 합성 표면 5종에 대한 실제 엔진 출력입니다. 초록 = OK, 빨강 = NG bbox + 면적 라벨.

| | | |
| --- | --- | --- |
| **OK (정상)** | **NG — scratch** | **NG — dot defects** |
| ![normal](docs/images/result_normal_surface.png) | ![scratch](docs/images/result_scratch_surface.png) | ![dots](docs/images/result_dot_defect_surface.png) |
| **NG — stain** | **NG — mixed** | |
| ![stain](docs/images/result_stain_surface.png) | ![mixed](docs/images/result_mixed_defects_surface.png) | |

5개 케이스 모두 의도한 룰을 정확히 트립:

| 이미지 | 판정 | 결함 수 | max area (mm²) | max length (mm) | 트립 룰 |
| --- | --- | ---: | ---: | ---: | --- |
| `normal_surface.png` | **OK** | 0 | 0.00 | 0.00 | — |
| `scratch_surface.png` | **NG** | 1 | 6.47 | 21.57 | length > 5.0 |
| `dot_defect_surface.png` | **NG** | 5 | 0.37 | 0.69 | count > 3 |
| `stain_surface.png` | **NG** | 1 | 25.33 | 7.08 | area > 2.0 + length > 5.0 |
| `mixed_defects_surface.png` | **NG** | 5 | 6.44 | 13.07 | 모든 룰 트립 |

### 12.2 성능 (macOS Intel x86_64, OpenCV 4.13, Release 빌드, `--benchmark 50`)

```bash
python scripts/benchmark_inspector.py --images data/sample_images --runs 50
```

| image | runs | avg (ms) | min | p50 | p95 | max | fps |
|---|---:|---:|---:|---:|---:|---:|---:|
| dot_defect_surface.png | 50 | 20.85 | 19.17 | 20.61 | 22.24 | 23.81 | 48.0 |
| mixed_defects_surface.png | 50 | 20.74 | 19.53 | 20.57 | 21.90 | 22.41 | 48.2 |
| normal_surface.png | 50 | 20.71 | 18.97 | 19.87 | 22.23 | 47.09 | 48.3 |
| scratch_surface.png | 50 | 20.78 | 19.64 | 20.63 | 22.24 | 22.62 | 48.1 |
| stain_surface.png | 50 | 12.06 | 11.25 | 11.84 | 13.52 | 14.09 | 82.9 |

512×512 단일 카메라 기준 **~50 fps** 처리. PNG I/O와 결과 이미지 저장을 포함한 end-to-end 사이클 타임이고, 알고리즘 자체는 더 짧습니다. 멀티 카메라 라인에서는 `InspectionEngine`의 stateless 설계 덕분에 인스펙션 큐를 멀티스레드로 확장 가능합니다.

### 12.3 합성 평가셋 — 두 operating point

80장 합성 평가셋 (정상 28장 + 결함 52장, 조명 그라데이션 + specular highlight + paint grain 포함):

```bash
python scripts/generate_eval_dataset.py --out data/eval --count 80 --seed 42
python scripts/evaluate_dataset.py --dataset data/eval --out data/eval_runs
```

| 설정 | accuracy | precision (NG) | recall (NG) | F1 (NG) | confusion (TP/TN/FP/FN) | 의미 |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| **default** (`min_contour_area_px=30`) | 0.650 | 0.650 | **1.000** | 0.788 | 52 / 0 / 28 / 0 | 모든 NG 검출, 정상의 specular highlight를 오인 |
| **tuned** (`min_contour_area_px=500`) | 0.838 | **1.000** | 0.750 | 0.857 | 39 / 28 / 0 / 13 | 오검출 0, 작은 dot 결함은 노이즈 floor 아래로 누락 |

실 라인 운영에서는 "부적합품 출하 위험 vs. 과검 비용"에 따라 둘 사이에서 튜닝합니다. 본 엔진은 두 operating point가 한 파라미터 변경으로 이동 가능하다는 점을 평가 하네스가 정량적으로 입증합니다. 카테고리별로는 **scratch/stain/mixed 결함은 두 설정 모두 100% 정확**, **dot 결함은 default에서 100% / tuned에서 0%**.

### 12.4 실 데이터셋 평가 — Magnetic Tile defect (392 images)

공개 표면 결함 데이터셋 [Magnetic-tile-defect-datasets](https://github.com/abin24/Magnetic-tile-defect-datasets) 을 동일 엔진으로 평가했습니다. 정상 200장 + 결함 192장 (5개 카테고리: Blowhole, Break, Crack, Fray, Uneven). 합성 데이터에 한 번도 노출된 적 없는 “first contact” 결과입니다.

```bash
git clone https://github.com/abin24/Magnetic-tile-defect-datasets..git /tmp/mtd
python scripts/prepare_magnetic_tile.py --src /tmp/mtd --out data/datasets/magnetic_tile
python scripts/evaluate_dataset.py --dataset data/datasets/magnetic_tile --out data/eval_runs/mtd_default
```

| 카테고리 | n | accuracy | recall (NG) |
| --- | ---: | ---: | ---: |
| MT_Blowhole | 40 | 1.00 | **1.00** |
| MT_Break | 40 | 1.00 | **1.00** |
| MT_Crack | 40 | 1.00 | **1.00** |
| MT_Fray | 32 | 1.00 | **1.00** |
| MT_Uneven | 40 | 1.00 | **1.00** |
| normal (MT_Free) | 200 | 0.00 | n/a (전부 false NG) |
| **overall** | **392** | **0.49** | **1.00** |

**모든 5개 결함 카테고리에서 100% recall — 어떤 결함도 놓치지 않음.** 동시에 200장 정상 타일 전체가 false NG로 잡힘. 시각적 원인은 명백합니다.

| 실 결함 (MT_Crack) — TP | 정상 (MT_Free) — FP |
| --- | --- |
| ![mtd-crack](docs/images/mtd/result_MT_Crack.png) | ![mtd-normal](docs/images/mtd/result_normal.png) |

자성 타일의 자연 결정/표면 grain이 “local mean보다 어두운 픽셀”이라는 adaptive threshold의 기준을 그대로 만족시키기 때문입니다. `--adaptive-block-size`, `--adaptive-c`, `--min-contour-area-px`, `--max-defect-count` 4축으로 그리드 sweep을 돌려도 default보다 의미 있게 좋은 operating point가 없습니다 (TP/TN 동시 향상이 안 됨 — 한쪽을 올리면 다른 쪽이 떨어짐).

**이것이 룰베이스 단독의 본질적 한계이고, 실제 라인 적용 시 다음 중 하나로 해결합니다:**

1. **광학/조명 보강** — dome light / coaxial light / polarizer 로 정반사·표면 grain의 시각적 영향을 줄임 (공고의 “2D/3D 광학계 및 조명 테스트” 업무 영역). 현재 엔진은 100% recall이므로 lighting 보강만으로도 normal grain이 약해지면 precision이 따라 올라옴.
2. **Cascade with learned classifier** — 룰베이스 엔진이 1차 후보를 100% recall로 잡고, CNN 분류기가 “텍스처 vs 진짜 결함”을 2차 분류. 룰베이스의 100% recall이 cascade의 floor 보장.
3. **Background model** — 정상 타일 N장으로 표면 텍스처의 통계 모델을 만들어 빼낸 후 잔차에 threshold. 본 POC 범위 밖.

**평가 하네스는 동일 CLI로 MVTec-AD / KolektorSDD2 / Severstal에 그대로 적용 가능**합니다. 절차는 [`docs/dataset_evaluation.md`](docs/dataset_evaluation.md) 참고.

### 12.5 3D stereo mini-demo

`scripts/stereo_demo.py`는 합성 스테레오 페어를 생성하고 StereoSGBM disparity + depth jump anomaly를 시각화합니다. "BUMP" 영역은 표면 휘도가 배경과 같지만 **깊이가 다르므로** 2D 룰베이스로는 못 잡고 3D만 잡을 수 있습니다.

![stereo](docs/images/stereo_depth_anomaly.png)

흰 영역이 BUMP (배경보다 가까움, 높은 disparity), 빨간 점은 “주변 median disparity와 4px 이상 차이” = depth anomaly. 자세한 내용은 [`docs/stereo_3d.md`](docs/stereo_3d.md).

### 12.6 JSON 리포트 스키마 (`scratch_surface.png` 실 출력)

```json
{
  "image_name": "scratch_surface",
  "result": "NG",
  "defect_count": 1,
  "max_area_mm2": 6.4675,
  "max_length_mm": 21.5672,
  "total_area_mm2": 6.4675,
  "created_at": "2026-05-16T...",
  "defects": [
    {
      "defect_id": 1,
      "bbox": {"x": 76, "y": 152, "w": 365, "h": 232},
      "center": {"x": 256.3, "y": 268.2},
      "area_px": 2587.0,
      "area_mm2": 6.4675,
      "length_px": 431.3,
      "length_mm": 21.5672
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
├── docs/                     # architecture / algorithm / sequence / optics /
│                             # cpp_design / dataset_evaluation / stereo_3d /
│                             # test_report
├── cpp/                      # C++ 검사 엔진 (CMake 빌드)
│   ├── CMakeLists.txt        # vision_inspector + (옵션) GoogleTest
│   ├── include/              # 헤더 (Engine / Preprocessor / Detector / Measurement / ReportWriter ...)
│   ├── src/                  # 구현 + main.cpp (--benchmark N 포함)
│   └── tests/                # GoogleTest 단위 테스트 (FetchContent)
├── app/streamlit_app.py      # Streamlit UI (C++ CLI 호출)
├── csharp_hmi/               # C# WinForms HMI (.NET 8, Windows)
│   └── VisionInspectorHmi/   #   동일 vision_inspector.exe 를 Process.Start
├── interface/                # PLC/Camera/Robot 시뮬레이터 + SequenceController
│   ├── plc_simulator.py      #   in-memory mock
│   └── plc_modbus.py         #   실 Modbus TCP 어댑터 (pymodbus)
├── scripts/                  # 샘플 이미지 합성, dataset 평가, 벤치마크, stereo demo,
│                             # C++ CLI Python wrapper
├── data/                     # sample_images/, results/, eval/, eval_runs/,
│                             # benchmark_runs/, stereo/  (대부분 gitignored)
└── tests/                    # pytest 단위/통합 테스트 (Python)
```

## 14. 기술 스택

- **C++17**, **OpenCV 4.x**, **CMake 3.14+**, **GoogleTest 1.14** (FetchContent)
- **Python 3.9+** (3.8도 동작), `streamlit`, `opencv-python`, `numpy`, `pandas`, `matplotlib`, `pytest`, `pillow`, `pymodbus`
- **C# / .NET 8 (WinForms)** — `csharp_hmi/VisionInspectorHmi`
- **Modbus TCP** — `pymodbus` (실 프로토콜 라운드트립 자체 테스트 포함)
- 빌드 / 실행: macOS, Ubuntu, Windows (CMake 표준 흐름, .NET은 Windows 실행)

## 15. 한계점

- 합성 + 1종 실 데이터셋 (Magnetic Tile, 392장) 검증까지 진행했으며, 실 광학계 / 조명 / 카메라 캘리브레이션은 적용되지 않았습니다. 실 데이터셋 결과는 §12.4에 정직하게 게시되어 있습니다 — 100% recall이지만 텍스처 풍부한 표면에서는 precision 0.49로, 룰베이스 단독의 한계가 정량적으로 드러납니다.
- 룰베이스 검사만 다루며 학습 기반 결함 분류(예: CNN segmentation)는 다루지 않습니다. 실 데이터 결과는 cascade(룰베이스 1차 후보 + 학습 분류기 2차) 또는 dome/coaxial 조명이 필수임을 시사합니다.
- Modbus TCP 어댑터는 실 프로토콜이지만 검증은 in-process pymodbus 서버에 대한 라운드트립 수준입니다. Robot은 여전히 in-memory 시뮬레이터입니다 (UR/ABB RTDE 어댑터는 향후 작업).
- 3D 데모는 합성 스테레오 페어로 disparity와 깊이 점프 가시화까지 보이는 mini-demo입니다 — 본격 point cloud / plane-fit 파이프라인은 후속 작업입니다.

## 16. 개선 방향

- MVTec-AD / KolektorSDD2 / Severstal 등 실데이터셋으로 임계값 그리드 서치 자동화 (현재 `evaluate_dataset.py` 위에 한 겹만 더 두면 됨)
- Pylon / Spinnaker / Vimba SDK를 사용하는 Camera 어댑터 추가 (`CameraSimulator` 대체)
- open62541(OPC-UA) / EtherCAT 어댑터, UR/ABB RTDE Robot 어댑터 추가 (현재 Modbus만 실 프로토콜)
- 결함 분류기(예: CNN segmentation) 추가 시 본 룰베이스 결과를 1차 필터로 두는 cascade 구조
- 3D 모듈을 실 스테레오 카메라 + plane-fit residual / point-cloud normal 기반으로 확장 (현재 합성 disparity demo)
- 멀티스레드 인스펙션 큐 (`InspectionEngine` stateless 설계 활용) — 1대 PC에서 다중 카메라 라인 처리
- GoogleTest 커버리지를 Preprocessor / DefectDetector 까지 확장 (현재 Measurement / Verdict / ReportWriter)

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
