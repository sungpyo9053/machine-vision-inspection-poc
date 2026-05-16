# 장비 시퀀스

실제 머신비전 검사 설비는 보통 PLC가 마스터 컨트롤러 역할을 한다. 본 POC는 동일한 흐름을 Python 시뮬레이터로 재현한다.

## 1 사이클 시퀀스

| Step | 주체 | 동작 | 로그 예시 |
| --- | --- | --- | --- |
| 1 | PLC | 부품이 검사 위치에 도착하면 트리거 ON | `[PLC] trigger_on plc=PLC-01` |
| 2 | Camera | 트리거를 받아 1 프레임 캡처, 라인 PC에 이미지 전송 | `[CAMERA] capture_frame image=sample_01.png` |
| 3 | Vision (C++) | 라인 PC가 `vision_inspector` CLI 실행, OpenCV 파이프라인 수행 | `[VISION] inspection_started` |
| 4 | Vision (C++) | 결함 후보 검출 / 측정 / OK·NG 판정 / JSON·PNG·CSV 저장 | `[VISION] defect_count=2 result=NG` |
| 5 | PLC | 라인 PC가 PLC 레지스터에 결과 기록 | `[PLC] write_result result=NG` |
| 6 | Robot | PLC 신호로 다음 작업 좌표 이동 (NG → 불량 박스, OK → 다음 공정) | `[ROBOT] move_next_position position=UNLOAD` |

## 시퀀스 코드 매핑

`interface/sequence_controller.py`의 `SequenceController.run_single_inspection()`이 위 단계를 그대로 수행한다.

```python
plc.trigger_on()
captured = camera.capture(image_path)
run = run_inspection(captured, output_dir, cfg)   # ← C++ CLI subprocess
plc.write_result(run.report["result"])
robot.move_next_position()
```

C++ 바이너리가 빌드되지 않은 환경에서도 PLC/Camera 단계 로그까지는 정상 발생하고, Vision 단계만 `error binary_missing`으로 빠진다. 이는 실제 설비에서 “라인 PC 측 SW 부재”에 해당하는 fault 상황을 흉내낸다.

## 실제 설비와의 차이점

- 본 POC의 PLC는 Modbus / OPC-UA / EtherCAT 연결 없이 메모리 상에서 상태만 갱신한다. 실 장비 적용 시 `plc_simulator.py`를 PyModbus / open62541 클라이언트로 치환하는 형태로 확장한다.
- Camera는 GigE Vision / USB3 Vision 대신 디스크의 PNG를 “캡처한 프레임”으로 반환한다. Pylon / Spinnaker / Vimba SDK 어댑터로 교체하면 동일 인터페이스가 유지된다.
- Robot은 좌표/속도 제어 없이 “다음 포지션” 인덱스만 순환한다. 실제 적용 시 UR/ABB/KUKA RTDE 등으로 교체한다.
