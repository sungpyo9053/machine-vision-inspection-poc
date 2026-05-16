# 3D 비전 mini-demo

채용 공고의 우대 항목 **"3D 비전 시스템 개발/구축/운영 경험"** 에 대응하기 위한 최소 데모입니다. 본격 3D 파이프라인이 아니라, **2D 룰베이스가 잡을 수 없는 표면 단차/돌출 결함을 disparity로 가시화**할 수 있다는 점을 보이는 것이 목적입니다.

## 흐름

```
synthetic left image
synthetic right image (baseline + extra shift on "bump" region)
        │
        ▼
StereoSGBM (numDisparities=32, blockSize=5)
        │
        ▼
disparity map  ──►  colourise (TURBO)
        │
        ▼
median filter + jump > 4 px  ──►  depth anomaly overlay (빨간 픽셀)
```

`scripts/stereo_demo.py`를 실행하면 다음이 생성됩니다.

```
data/stereo/
  left.png
  right.png
  disparity.png        # 컬러맵 적용
  depth_anomaly.png    # 깊이 점프 영역을 빨간색으로 표시
```

## 실제 설비 적용 시 확장 포인트

- **합성 스테레오 → 실 스테레오 카메라**: ZED / RealSense / Basler 두 대 + 캘리브레이션 데이터(camera matrix, distortion, rectification, Q)
- **disparity 임계 → plane-fit residual**: 검사면을 RANSAC으로 평면 피팅한 뒤 잔차가 임계 이상인 픽셀을 결함으로 본다
- **point cloud → 표면 정상(normal) 분석**: 도장면 dent / pop-out, 단차 결함 검출
- **2D + 3D cascade**: 본 POC의 C++ 룰베이스 엔진이 1차로 결함 후보(스크래치/얼룩/이물)를 검출하고, 3D 모듈이 2차로 단차 결함을 검출하는 구조

## 한계

- 합성 좌우 페어이므로 occlusion / specular highlight 영향은 재현되지 않음
- StereoSGBM 파라미터는 본 데모의 합성 데이터에 맞춘 값. 실데이터에서는 튜닝 필요
- 실 3D 검사는 결국 **point cloud 처리(PCL, Open3D)** 가 핵심이며, 본 데모는 그 전 단계까지만 다룬다
