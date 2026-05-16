# C# WinForms HMI (선택)

Streamlit UI와 동일한 책임을 갖는 **C# WinForms 데모**입니다. 동일한 `vision_inspector` 바이너리를 `Process.Start`로 호출하므로 검사 로직(C++) 자체는 한 줄도 중복되지 않습니다.

채용 공고의 우대 항목 **“개발언어: C#, C++(중)”** 에 대응하기 위해 추가한 레이어입니다.

## 디자인

```
MainForm  ──►  InspectorRunner.RunAsync(imagePath)
                    │
                    ├── FindBinary()              ← build/, cpp/build/, Debug/, Release/ 자동 탐색
                    ├── Process.Start(vision_inspector …)
                    └── JsonSerializer.Deserialize<InspectionReport>(...)
                                  ▲
                                  └── C++ ReportWriter::saveJsonReport 의 스키마와 1:1 매칭
```

`InspectorRunner`는 Python 측 `scripts/run_cpp_inspector.py`와 인자/탐색 순서가 같아서 두 UI가 같은 결과를 만든다.

## 빌드 / 실행 (Windows)

```powershell
dotnet build csharp_hmi/VisionInspectorHmi
dotnet run --project csharp_hmi/VisionInspectorHmi
```

- 타깃 프레임워크는 `net8.0-windows`. WinForms 런타임이 Windows 전용이라 macOS/Linux에서는 빌드는 가능하지만 실행은 Windows에서만 됩니다.
- 실행은 보통 레포 루트에서 합니다 (HMI가 `build/`, `cpp/build/` 등을 상대 경로로 탐색).

## macOS/Linux에서 빌드만 확인하고 싶을 때

```bash
dotnet restore csharp_hmi/VisionInspectorHmi
dotnet build   csharp_hmi/VisionInspectorHmi -c Release -p:EnableWindowsTargeting=true
```

(실행은 Windows 머신 또는 Windows VM 필요)

## 화면 구성

- 상단: 이미지 파일 선택
- 중단: 임계 파라미터 5종 (Python UI와 동일 — `pixel_to_mm`, `max_defect_count`, `max_area_mm2`, `max_length_mm`, `min_contour_area_px`)
- 좌·우: 원본 / 결과 PictureBox
- 하단: 큰 OK/NG 라벨 + 지표 + stdout / stderr 로그

## 의도적으로 작게 만든 이유

이 폴더는 “HMI 풀스택”이 아니라 “동일 C++ 코어가 Python UI와 C# UI에서 동일하게 동작한다”는 사실을 보이기 위한 최소 데모입니다. 실 라인 적용 시:

- 인증 / 사용자 권한 / 운영 로그는 C# 측에 추가
- 통신 모듈은 `InspectorRunner` 옆에 `ModbusClient` 등으로 확장
- 운영 화면은 `MainForm`에서 사이클 그래프, NG 박스 좌표 가시화, 트레이스 검색 등으로 확장
