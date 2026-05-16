"""Streamlit front end for the C++ surface defect inspector.

The UI does no image processing of its own. It uploads (or selects) a sample
image, calls the C++ ``vision_inspector`` binary via the
``run_cpp_inspector`` wrapper, and renders the JSON report and overlay image
the engine produced.

Run with:
    streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from typing import Optional

import pandas as pd
import streamlit as st

# Make sure ``scripts`` / ``interface`` resolve regardless of how Streamlit
# launches the script.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from scripts.run_cpp_inspector import (  # noqa: E402
    InspectorBinaryNotFound,
    InspectorConfig,
    InspectorRunError,
    find_inspector_binary,
    run_inspection,
)

SAMPLE_DIR = os.path.join(_REPO_ROOT, "data", "sample_images")
RESULTS_DIR = os.path.join(_REPO_ROOT, "data", "results")


def _list_sample_images() -> list:
    if not os.path.isdir(SAMPLE_DIR):
        return []
    return sorted(
        f for f in os.listdir(SAMPLE_DIR)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))
    )


def _save_uploaded_to_temp(uploaded) -> Optional[str]:
    if uploaded is None:
        return None
    suffix = os.path.splitext(uploaded.name)[1] or ".png"
    fd, path = tempfile.mkstemp(prefix="upload_", suffix=suffix,
                                dir=tempfile.gettempdir())
    with os.fdopen(fd, "wb") as fh:
        fh.write(uploaded.getbuffer())
    return path


def _verdict_banner(result: str) -> None:
    if result == "OK":
        st.success(f"### Verdict: **{result}**")
    elif result == "NG":
        st.error(f"### Verdict: **{result}**")
    else:
        st.warning(f"### Verdict: **{result or 'UNKNOWN'}**")


def main() -> None:
    st.set_page_config(page_title="C++ Vision Inspector", layout="wide")
    st.title("C++ Machine Vision Inspection System POC")
    st.write(
        "C++ OpenCV 기반의 표면 결함 검사 엔진을 호출하는 Streamlit 데모입니다. "
        "Python 쪽에서는 어떤 이미지 처리도 하지 않고, ``vision_inspector`` "
        "CLI를 그대로 실행한 뒤 생성된 JSON / 결과 이미지를 표시합니다."
    )

    # --- sidebar ---------------------------------------------------------
    st.sidebar.header("입력")
    upload = st.sidebar.file_uploader("이미지 업로드", type=["png", "jpg", "jpeg", "bmp"])
    samples = _list_sample_images()
    sample_choice = st.sidebar.selectbox(
        "또는 샘플 이미지 선택",
        options=["(선택 안 함)"] + samples,
        index=0,
    )

    st.sidebar.header("검사 파라미터")
    pixel_to_mm = st.sidebar.number_input(
        "pixel_to_mm_ratio", min_value=0.001, max_value=10.0, value=0.05,
        step=0.005, format="%.4f")
    max_defect_count = st.sidebar.number_input(
        "max_defect_count", min_value=0, max_value=999, value=3, step=1)
    max_defect_area_mm2 = st.sidebar.number_input(
        "max_defect_area_mm2", min_value=0.0, max_value=10000.0,
        value=2.0, step=0.1, format="%.2f")
    max_defect_length_mm = st.sidebar.number_input(
        "max_defect_length_mm", min_value=0.0, max_value=10000.0,
        value=5.0, step=0.1, format="%.2f")
    min_contour_area_px = st.sidebar.number_input(
        "min_contour_area_px", min_value=1, max_value=100000, value=30, step=1)

    binary = find_inspector_binary()
    if binary is None:
        st.sidebar.error(
            "vision_inspector 바이너리를 찾을 수 없습니다.\n\n"
            "먼저 빌드해 주세요:\n"
            "```\ncmake -S cpp -B build\ncmake --build build\n```"
        )
    else:
        st.sidebar.success(f"binary: {os.path.relpath(binary, _REPO_ROOT)}")

    run_clicked = st.sidebar.button("검사 시작", type="primary",
                                    disabled=binary is None)

    # --- choose image ----------------------------------------------------
    image_path: Optional[str] = None
    if upload is not None:
        image_path = _save_uploaded_to_temp(upload)
    elif sample_choice != "(선택 안 함)":
        image_path = os.path.join(SAMPLE_DIR, sample_choice)

    col_orig, col_result = st.columns(2)
    with col_orig:
        st.subheader("원본 이미지")
        if image_path and os.path.isfile(image_path):
            st.image(image_path, channels="BGR" if False else "RGB",
                     use_container_width=True)
        else:
            st.info("좌측 사이드바에서 이미지를 선택하거나 업로드해 주세요.")

    # --- run -------------------------------------------------------------
    if run_clicked:
        if image_path is None or not os.path.isfile(image_path):
            st.warning("먼저 검사할 이미지를 선택하거나 업로드해 주세요.")
            return

        cfg = InspectorConfig(
            pixel_to_mm=float(pixel_to_mm),
            max_defect_count=int(max_defect_count),
            max_defect_area_mm2=float(max_defect_area_mm2),
            max_defect_length_mm=float(max_defect_length_mm),
            min_contour_area_px=int(min_contour_area_px),
        )

        os.makedirs(RESULTS_DIR, exist_ok=True)
        with st.spinner("vision_inspector 실행 중..."):
            try:
                run = run_inspection(image_path, RESULTS_DIR, cfg, binary=binary)
            except InspectorBinaryNotFound as e:
                st.error(str(e))
                return
            except InspectorRunError as e:
                st.error(str(e))
                return

        report = run.report or {}

        with col_result:
            st.subheader("검사 결과 이미지")
            if run.result_image_path and os.path.isfile(run.result_image_path):
                st.image(run.result_image_path, use_container_width=True)
            else:
                st.warning("결과 이미지를 찾을 수 없습니다.")

        st.divider()
        _verdict_banner(report.get("result", "UNKNOWN"))

        metrics = st.columns(4)
        metrics[0].metric("결함 개수", report.get("defect_count", 0))
        metrics[1].metric("최대 면적 (mm²)",
                          f"{report.get('max_area_mm2', 0):.4f}")
        metrics[2].metric("최대 길이 (mm)",
                          f"{report.get('max_length_mm', 0):.4f}")
        metrics[3].metric("총 결함 면적 (mm²)",
                          f"{report.get('total_area_mm2', 0):.4f}")

        defects = report.get("defects", [])
        if defects:
            df = pd.DataFrame([{
                "id": d.get("defect_id"),
                "bbox_x": d.get("bbox", {}).get("x"),
                "bbox_y": d.get("bbox", {}).get("y"),
                "bbox_w": d.get("bbox", {}).get("w"),
                "bbox_h": d.get("bbox", {}).get("h"),
                "area_px": d.get("area_px"),
                "area_mm2": d.get("area_mm2"),
                "length_px": d.get("length_px"),
                "length_mm": d.get("length_mm"),
            } for d in defects])
            st.subheader("결함 리스트")
            st.dataframe(df, use_container_width=True)

        with st.expander("검사 로그 / 경로"):
            st.code(" ".join(run.args), language="bash")
            if run.stdout:
                st.text(run.stdout)
            if run.stderr:
                st.text(run.stderr)
            st.write(f"JSON 리포트: `{run.json_report_path}`")
            st.write(f"결과 이미지: `{run.result_image_path}`")
            st.write(f"누적 CSV: "
                     f"`{os.path.join(RESULTS_DIR, 'inspection_results.csv')}`")


if __name__ == "__main__":
    main()
