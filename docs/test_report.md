# 테스트 리포트

본 POC는 두 단계 테스트 전략을 사용한다.

1. **Python 단위/통합 테스트** — pytest 기반. OpenCV 빌드 없이도 항상 실행 가능.
2. **C++ CLI 통합 테스트** — `vision_inspector` 바이너리가 존재하면 자동으로 실행, 없으면 자동으로 skip.

## 테스트 종류

| 파일 | 종류 | 빌드 필요 여부 |
| --- | --- | --- |
| `tests/test_sample_generator.py` | 샘플 이미지 합성기 결정성/형상 검증 | ❌ |
| `tests/test_sequence_controller.py` | PLC/Camera/Robot 시뮬레이터 로그 + 시퀀스 컨트롤러 동작 | ❌ (바이너리 없으면 ERROR 분기 검증) |
| `tests/test_cpp_cli.py` | `vision_inspector` CLI 실행 / JSON 스키마 / OK·NG 분류 / CSV append | ✅ 바이너리 필요 |

## 실행 방법

```bash
pytest -v
```

C++ 바이너리가 없으면 `test_cpp_cli.py`는 다음과 같이 자동 skip된다.

```
tests/test_cpp_cli.py::test_help_runs SKIPPED (vision_inspector binary not built ...)
```

## 합성 이미지 기반 검증 결과

기본 설정(`pixel_to_mm=0.05`, `min_contour_area_px=30`, `max_defect_count=3`, `max_defect_area_mm2=2.0`, `max_defect_length_mm=5.0`)에서 다음을 기대한다.

| 이미지 | 기대 판정 | 트립 조건 |
| --- | --- | --- |
| `normal_surface.png` | **OK** | 노이즈/조명 변화만 있을 뿐 결함 없음 |
| `scratch_surface.png` | **NG** | 긴 사선 스크래치 → `max_length_mm` 초과 |
| `dot_defect_surface.png` | **NG** | 5개의 점 결함 → `max_defect_count` 초과 |
| `stain_surface.png` | **NG** | 큰 얼룩 → `max_area_mm2` 초과 |
| `mixed_defects_surface.png` | **NG** | 스크래치 + 얼룩 + 점 결함 동시 발생 |

`test_cpp_cli.py::test_normal_surface_is_ok`, `test_scratch_surface_detects_defect`, `test_csv_is_appended`가 위 케이스 중 핵심을 자동 검증한다.

## 한계점

- 합성 이미지는 실제 도장면 / 금속 / 플라스틱의 specular highlight / 텍스처 패턴을 완벽히 재현하지 않는다. 실데이터 검증 시 임계값과 morphology 커널 크기를 재튜닝해야 한다.
- C++ 측에 GoogleTest 같은 단위 테스트 프레임워크는 아직 없다. 현재는 CLI 통합 테스트만으로 회귀를 잡는다.
- 카메라 캘리브레이션, 동적 노출 보정, 멀티프레임 합성은 본 POC 범위 밖이다.
