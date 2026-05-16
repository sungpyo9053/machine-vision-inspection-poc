# 검사 알고리즘

C++ `InspectionEngine::inspect()`의 처리 흐름을 단계별로 정리한다.
모든 단계는 OpenCV C++ API를 사용하며 Python 측에서 재구현하지 않는다.

## 처리 파이프라인

```
Image
  │
  ▼
toGray()         ─ BGR → Gray 변환
  │
  ▼
applyCLAHE()     ─ Contrast Limited Adaptive Histogram Equalization
  │
  ▼
denoise()        ─ GaussianBlur(5×5, σ=1.2)
  │
  ▼
thresholdImage() ─ adaptiveThreshold(GAUSSIAN_C, BINARY_INV, 51, 10) ∨ Canny(50,150)
  │                + morphology close → open (3×3 ellipse)
  ▼
findContours()   ─ RETR_EXTERNAL, CHAIN_APPROX_SIMPLE
  │
  ▼
filterNoise()    ─ area < min_contour_area_px 인 contour 제거
  │
  ▼
measureDefect()  ─ bbox / center(moments) / minAreaRect 기반 length
  │
  ▼
pxToMm / pxAreaToMm2 ─ pixel_to_mm_ratio 적용
  │
  ▼
verdict()        ─ OK / NG 판정
```

## 각 단계의 목적

- **grayscale 변환**: 검사 대상이 단색 표면이라 채널 정보 없이도 결함 후보를 충분히 분리할 수 있다. 메모리/연산 비용을 줄이는 동시에 후속 알고리즘의 입력 가정과도 맞춘다.
- **CLAHE**: 도장면/금속 표면은 조명 위치에 따라 좌우 밝기 차이가 크다. 전역 히스토그램 평활화는 하이라이트 영역에서 결함을 깎아먹지만, CLAHE는 8×8 타일 단위로 보정해서 국소 명암을 살린다.
- **GaussianBlur**: 센서 노이즈와 텍스처 그레인이 contour 단계에서 false positive를 만든다. 작은 5×5 커널로 가볍게 평활화해서 노이즈만 죽이고 결함의 경계는 유지한다.
- **Adaptive threshold + Canny 동시 사용**: 얼룩/이물처럼 면적이 있는 결함은 `cv::adaptiveThreshold(GAUSSIAN_C, BINARY_INV, blockSize=51, C=10)`가 잘 분리한다. 51×51 local mean보다 10 이상 어두운 픽셀만 foreground로 잡으므로, 평탄한 표면(정상 부품)에서는 거의 foreground가 생기지 않는다. **Otsu를 쓰지 않는 이유**: Otsu는 결함이 없는 이미지에서도 늘 어떤 threshold를 만들기 때문에, 약한 조명 그라데이션만 있어도 “어두운 쪽 절반”을 거대 foreground 블롭으로 잡아 phantom NG를 낸다. Adaptive는 local mean이 표면을 따라가므로 이런 오판이 없다. 한편 스크래치처럼 “내부가 주변보다 크게 어둡진 않지만 엣지 응답은 강한” 결함은 adaptive가 놓치므로 Canny를 함께 OR한다.
- **morphology close → open**: 스크래치 엣지가 점선처럼 끊겨서 contour가 잘게 쪼개지는 것을 close가 메운다. 그 다음 open으로 살아남은 1~2 px짜리 노이즈를 제거한다.
- **contour 검출**: `RETR_EXTERNAL`로 외곽만 추출한다. 결함 내부의 hole까지 잡으면 한 결함이 여러 개로 카운트되어 판정이 흔들린다.
- **노이즈 필터**: 픽셀 단위 최소 면적(`min_contour_area_px`, 기본 30 px) 이하의 contour를 버린다.
- **bbox / center / length**: 측정은 `boundingRect` (bbox), `moments`(중심), `minAreaRect`(최대 변 길이)로 수행한다. 사선 결함의 길이를 축 정렬 bbox로 재면 과소평가되므로 회전 사각형의 긴 변을 사용한다.
- **mm 변환**: `pixel_to_mm_ratio`(=1px가 몇 mm인지) 한 값으로 길이/면적을 mm 단위로 변환한다. 면적은 ratio²을 곱한다.

## OK / NG 판정 기준

다음 조건 중 하나라도 만족하면 **NG**다.

- `defect_count > max_defect_count`
- `max_area_mm² > max_defect_area_mm2`
- `max_length_mm > max_defect_length_mm`

위 세 조건을 모두 통과하면 **OK**이다.

이 룰베이스 판정 기준은 실제 도장면 검사 설비에서 자주 쓰는 “개수 / 면적 / 길이” 3-축 룰을 단순화한 것이다. 추가로 위치별 마스크나 클러스터링 룰을 적용하는 형태로 쉽게 확장할 수 있다.

## 파라미터 가이드

| 파라미터 | 기본값 | 영향 |
| --- | --- | --- |
| `pixel_to_mm_ratio` | 0.05 | 광학계 / 작업 거리 따라 캘리브레이션. 1 px = 50 µm 가정 |
| `min_contour_area_px` | 30 | 작을수록 검출 민감도↑, 노이즈↑ |
| `max_defect_count` | 3 | 허용 결함 개수 |
| `max_defect_area_mm2` | 2.0 | 얼룩/이물 등 면적 결함 허용치 |
| `max_defect_length_mm` | 5.0 | 스크래치 등 선형 결함 허용치 |
