# 테스트 리포트

본 POC는 세 단계 테스트 전략을 사용한다.

1. **Python pytest** — 시뮬레이터 / 시퀀스 컨트롤러 / 데이터셋 평가 하네스 / Modbus 어댑터 / stereo demo. OpenCV 빌드 없이 항상 실행 가능.
2. **C++ GoogleTest** — `vision_inspector_core` 정적 라이브러리에 대한 단위 테스트. CMake가 `FetchContent`로 GoogleTest를 자동 다운로드한다.
3. **C++ CLI 통합 테스트** — `vision_inspector` 바이너리가 존재하면 자동으로 실행, 없으면 자동으로 skip.

## Python 테스트 매트릭스

| 파일 | 검증 대상 | 빌드 필요 여부 |
| --- | --- | --- |
| `tests/test_sample_generator.py` | 합성 샘플 이미지 결정성/형상 | ❌ |
| `tests/test_sequence_controller.py` | PLC/Camera/Robot 시뮬레이터 + 시퀀스 컨트롤러 (binary missing 분기 포함) | ❌ |
| `tests/test_modbus_plc.py` | pymodbus 기반 PLC 어댑터 — in-process 서버에 대한 trigger / write_result / read_status 라운드트립 | ❌ |
| `tests/test_eval_harness.py` | 데이터셋 평가기 (`labels.csv` 로더, 혼동행렬 계산식, 엔드-투-엔드) | C++ 빌드 시 추가 실행 |
| `tests/test_benchmark_parser.py` | C++ `--benchmark` 출력 파서 정규식 | ❌ |
| `tests/test_stereo_demo.py` | StereoSGBM disparity, depth anomaly 합성 검증 | ❌ |
| `tests/test_cpp_cli.py` | `vision_inspector` CLI / JSON 스키마 / OK·NG 분류 / CSV append | ✅ C++ 바이너리 필요 |

현재 머신 상태(OpenCV/CMake 미설치) 기준 실행 결과: **15 passed, 5 skipped**.

## C++ GoogleTest 매트릭스

| 파일 | 검증 대상 |
| --- | --- |
| `cpp/tests/test_measurement.cpp` | `Measurement::pxToMm`, `pxAreaToMm2`, `measureDefect` (사각형 / 대각선 케이스) |
| `cpp/tests/test_verdict.cpp` | `InspectionEngine::verdict` OK/NG 경계 + 트립 조건별 단위 검증 |
| `cpp/tests/test_report_writer.cpp` | JSON 스키마 / CSV append (헤더 한 번) / JSON 문자열 이스케이프 |

실행:

```bash
cmake -S cpp -B build -DVISION_INSPECTOR_BUILD_TESTS=ON
cmake --build build
ctest --test-dir build --output-on-failure
```

## 합성 이미지 기반 검증 결과 (기본 임계 기준)

| 이미지 | 기대 판정 | 트립 조건 |
| --- | --- | --- |
| `normal_surface.png` | **OK** | 노이즈/조명 변화만 있을 뿐 결함 없음 |
| `scratch_surface.png` | **NG** | 긴 사선 스크래치 → `max_length_mm` 초과 |
| `dot_defect_surface.png` | **NG** | 5개의 점 결함 → `max_defect_count` 초과 |
| `stain_surface.png` | **NG** | 큰 얼룩 → `max_area_mm2` 초과 |
| `mixed_defects_surface.png` | **NG** | 스크래치 + 얼룩 + 점 결함 동시 발생 |

`test_cpp_cli.py::test_normal_surface_is_ok`, `test_scratch_surface_detects_defect`, `test_csv_is_appended`가 이 중 핵심을 자동 검증한다.

## Dataset evaluation harness 적용 (공개 결함 데이터셋)

`scripts/evaluate_dataset.py`는 임의 라벨 폴더(`labels.csv`)에 대해 검사를 일괄 실행하고 다음을 출력한다.

```
predictions.csv          # 이미지별 예측/GT/elapsed_ms
confusion_matrix.csv     # 2x2 OK/NG
summary.json             # accuracy / precision_NG / recall_NG / F1_NG / per-category / avg_elapsed_ms
```

MVTec-AD / KolektorSDD2 / Severstal 등 공개 데이터셋 적용 절차는 [`docs/dataset_evaluation.md`](dataset_evaluation.md) 참고.

## 성능 측정

`vision_inspector --benchmark N` 으로 같은 이미지를 N회 반복 측정한 통계가 한 줄로 출력된다.

```
benchmark runs=50 image=... avg_ms=12.3 min_ms=10.1 p50_ms=12.0 p95_ms=18.5 max_ms=20.4 fps=81.3
```

`scripts/benchmark_inspector.py`로 한 폴더 전체 이미지를 일괄 측정하고 `benchmark.md` (Markdown 표) / `benchmark.csv`를 만든다.

## 한계점

- 합성 이미지는 실제 도장면 / 금속 / 플라스틱의 specular highlight / 텍스처 패턴을 완벽히 재현하지 않는다. 공개 결함 데이터셋 검증 시 임계값과 morphology 커널 크기 재튜닝이 필요하다.
- Modbus 어댑터는 in-process pymodbus 서버에 대한 라운드트립까지 검증한다. 실 PLC 적용 시 vendor-specific 변환(예: ABB / Siemens float layout)이 필요할 수 있다.
- GoogleTest 커버리지는 `Measurement` / `verdict` / `ReportWriter` 중심이며 `Preprocessor`, `DefectDetector`의 OpenCV 의존 부분은 CLI 통합 테스트로 회귀한다.
