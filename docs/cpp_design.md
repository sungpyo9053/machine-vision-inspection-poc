# C++ 검사 엔진 설계

C++ 코어 엔진은 단일 책임 원칙(SRP)에 따라 5개의 협업 클래스로 분리되어 있다.
모든 클래스는 `mvi` 네임스페이스에 속하며, 외부 의존성은 OpenCV (core / imgproc / imgcodecs) 뿐이다. JSON은 외부 라이브러리 없이 직접 만든 작은 writer(`ReportWriter::saveJsonReport`)로 처리한다.

## 클래스 구조

```
InspectionEngine ─┬─► Preprocessor      (전처리)
                  ├─► DefectDetector    (contour + 노이즈 필터)
                  ├─► Measurement       (bbox / center / length / mm 변환)
                  └─► ReportWriter      (PNG / JSON / CSV)
```

- `InspectionEngine::inspect()` 한 함수가 “이미지 경로 + 설정 → InspectionResult” 매핑을 책임진다.
- 각 보조 클래스는 의도적으로 stateless이다. 동일 엔진 객체를 여러 스레드에서 동시에 호출해도 문제가 없다.

## 데이터 구조

| Struct | 필드 | 비고 |
| --- | --- | --- |
| `InspectionConfig` | `pixelToMmRatio`, `minContourAreaPx`, `maxDefectCount`, `maxDefectAreaMm2`, `maxDefectLengthMm` | CLI 인자가 그대로 매핑됨 |
| `Defect` | `id`, `bbox`(cv::Rect), `center`(cv::Point2f), `areaPx/areaMm2`, `lengthPx/lengthMm` | 단일 결함 한 건 |
| `InspectionResult` | `imageName`, `result`, `defectCount`, `maxAreaMm2`, `maxLengthMm`, `totalAreaMm2`, `defects`, `createdAt`, `resultImagePath`, `jsonReportPath` | 1회 검사 결과 |

## CLI / UI 분리 이유

- 핵심 검사 로직은 검사 결과의 재현성과 성능을 위해 **C++ + OpenCV 단일 바이너리**로 묶는다.
- UI / 시퀀스 / 시뮬레이터는 빠른 반복 개발과 시각화가 중요한 영역이므로 **Python**으로 둔다.
- 이 분리는 다음 두 가지 이점을 가진다.
  1. 같은 C++ 바이너리를 **장비 라인 PC, CI, GUI 데모 어디서나 동일하게 호출**할 수 있다.
  2. UI/시퀀스의 변경이 검사 알고리즘에 영향을 주지 않는다. Python을 갈아 끼우거나, C# WinForms로 다시 짜더라도 C++ 엔진은 그대로 재사용된다.

## 자율주행 / HD Map 경험과의 연결

기존 자율주행 / HD Map 프로젝트에서 다음과 같은 C++ 설계 패턴을 반복적으로 적용했다.

- 대용량 공간 데이터(타일 단위 HD Map, 코스트맵)를 **stateless engine + struct 입출력** 형태로 다뤘다.
- 경로탐색 결과를 “룰 기반 후처리(차선 변경 안전성, 최대 속도 제한 등)”로 검증했다.
- 성능을 위해 OpenMP / 메모리 풀 / 캐시 친화 구조를 직접 설계했다.

본 검사 엔진도 동일한 사고방식으로 만들었다.

- `Preprocessor / DefectDetector / Measurement`는 stateless로 두어, 추후 멀티스레드 인스펙션 큐를 붙여도 락 추가 없이 동시 실행 가능하다.
- “contour → bbox/length → mm 변환 → 룰 비교” 흐름은 “경로 → 비용 함수 → 룰 위반 검사 → 통과/실패 판정”과 같은 구조다. 룰 추가 시 `verdict()` 한 군데만 확장하면 된다.
- CSV append 방식의 누적 리포트는 자율주행 시뮬레이션 결과 로그를 누적·집계하던 패턴과 동일하다.

## 확장 포인트

- **C# WinForms HMI** 추가: 동일 `vision_inspector` CLI를 `Process.Start`로 호출만 하면 같은 결과를 받을 수 있다. (실제 설비 HMI 측 요구가 있을 경우 1차 후보.)
- **gRPC / shared memory 호출**: subprocess 오버헤드가 부담될 만큼 cycle time이 짧아지면, 검사 엔진을 라이브러리로 빌드해 라인 PC 프로세스에 임베드한다.
- **C++ unit test**: GoogleTest 도입은 본 버전에서 제외했지만 `Measurement::pxToMm` 류 함수는 그대로 테스트 가능한 형태로 노출되어 있다.
