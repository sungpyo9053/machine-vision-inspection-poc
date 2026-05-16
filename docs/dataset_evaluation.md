# 데이터셋 평가 (real-world)

본 POC의 검사 엔진은 합성 이미지로 1차 검증되어 있지만, 실 운영 신뢰성을 보이려면 공개 표면 결함 데이터셋으로 같은 파이프라인을 돌려서 혼동행렬을 보는 것이 필요하다. 이 페이지는 그 절차를 정리한다.

## 1. 평가 하네스 구조

```
scripts/
  generate_eval_dataset.py   # 라벨이 있는 합성 평가셋 생성 (40+ 장)
  evaluate_dataset.py        # 임의 라벨 폴더에 대해 일괄 검사 + 혼동행렬
```

`labels.csv` 스키마:

```
image,expected,category
img_0000_normal.png,OK,normal
img_0014_scratch.png,NG,scratch
...
```

`evaluate_dataset.py`는 모든 이미지에 대해 `vision_inspector` CLI를 실행하고 다음을 생성한다.

- `predictions.csv` — 이미지별 예측/GT/사이클 타임
- `confusion_matrix.csv` — 2×2 OK/NG
- `summary.json` — accuracy / precision / recall / F1 / per-category 통계 / 평균 cycle time

## 2. 합성 평가셋으로 회귀 확인

```bash
python scripts/generate_eval_dataset.py --out data/eval --count 40
cmake -S cpp -B build && cmake --build build      # 최초 1회
python scripts/evaluate_dataset.py --dataset data/eval --out data/eval_runs
```

결과 예시 (40장, 기본 임계):

```
accuracy       : 0.875
precision (NG) : 0.929
recall (NG)    : 0.897
F1 (NG)        : 0.912
```

정확한 수치는 시드/환경에 따라 변동 가능. CI에서는 `tests/test_eval_harness.py`가 이 흐름을 더 작은 샘플 수로 자동 회귀한다.

## 3. MVTec-AD 적용 절차

[MVTec AD](https://www.mvtec.com/company/research/datasets/mvtec-ad)는 학술용으로 무료 배포되며 자동차 도장면과 가장 가까운 카테고리는 **`metal_nut`, `bottle`, `screw`** 정도이다 (도장 자체는 없음).

1. MVTec-AD를 다운로드한 뒤 카테고리 하나(`metal_nut/test`)를 골라 OK/NG 라벨로 정리한다.
   - `metal_nut/test/good/*.png` → `OK`
   - `metal_nut/test/<defect_type>/*.png` → `NG`
2. `labels.csv`를 만든다.
3. `evaluate_dataset.py --dataset <폴더> --pixel-to-mm <캘리브레이션 값>` 으로 일괄 평가.
4. 결과 confusion / 사이클 타임을 README의 “실데이터 결과” 표에 추가한다.

> 자동차 도장면 검사 설비 광학/조명 엔지니어링 경험까지 시연하려면 **MVTec-AD `metal_nut` + 합성 도장 결함**으로 두 케이스를 같이 보여주는 것이 효과적이다.

## 4. KolektorSDD2 / Severstal Steel Defect

연속 강판/스틸 표면이라 광학적으로는 자동차 도장면과 더 가깝다.

- KolektorSDD2: 학술 배포, 회원가입 필요
- Severstal Steel Defect Detection (Kaggle): 라이센스 확인 필요

본 하네스의 `labels.csv` 형식만 맞추면 동일 명령으로 평가 가능하다.

## 5. 한계

- 본 엔진은 룰베이스다. 데이터셋 간 광학 조건 차이가 크면 임계값을 카테고리별로 다시 튜닝해야 한다. `evaluate_dataset.py`에 `--max-defect-area-mm2` 등 모든 임계가 인자로 노출되어 있으므로, 그리드 서치 스크립트를 위에 한 겹 더 두면 자동 튜닝까지 확장 가능하다.
- 학습 기반(분류기/세그멘테이션)이 필요한 카테고리에서는 본 엔진이 1차 후보 검출 + 학습 모델이 2차 분류, 두 단계 cascade로 활용하는 것을 권장한다.
