#include <gtest/gtest.h>

#include <opencv2/imgproc.hpp>

#include "InspectionConfig.hpp"
#include "Measurement.hpp"

using mvi::InspectionConfig;
using mvi::Measurement;

TEST(MeasurementUnit, PxToMmAppliesRatio) {
    Measurement m;
    EXPECT_DOUBLE_EQ(m.pxToMm(100.0, 0.05), 5.0);
    EXPECT_DOUBLE_EQ(m.pxToMm(0.0, 0.05), 0.0);
    EXPECT_DOUBLE_EQ(m.pxToMm(200.0, 0.10), 20.0);
}

TEST(MeasurementUnit, PxAreaToMm2UsesSquareOfRatio) {
    Measurement m;
    // 100 px² with 1 px = 0.05 mm  ->  0.0025 mm² per px²  ->  0.25 mm²
    EXPECT_DOUBLE_EQ(m.pxAreaToMm2(100.0, 0.05), 0.25);
    EXPECT_DOUBLE_EQ(m.pxAreaToMm2(0.0, 0.05), 0.0);
}

TEST(MeasurementUnit, MeasureSquareContour) {
    // 50x50 axis-aligned square contour -> 2500 px² area, length 50 px.
    std::vector<cv::Point> contour = {
        {100, 100}, {150, 100}, {150, 150}, {100, 150}
    };
    InspectionConfig cfg;
    cfg.pixelToMmRatio = 0.1;

    Measurement m;
    auto d = m.measureDefect(7, contour, cfg);
    EXPECT_EQ(d.id, 7);
    EXPECT_EQ(d.bbox.width, 50);
    EXPECT_EQ(d.bbox.height, 50);
    EXPECT_NEAR(d.areaPx, 2500.0, 1.0);          // OpenCV uses Green's theorem
    EXPECT_NEAR(d.areaMm2, 25.0, 0.05);          // 2500 * 0.1 * 0.1
    EXPECT_NEAR(d.lengthPx, 50.0, 1.0);          // square -> 50 px side
    EXPECT_NEAR(d.lengthMm, 5.0, 0.1);
    // Centre near (125, 125)
    EXPECT_NEAR(d.center.x, 125.0f, 1.0f);
    EXPECT_NEAR(d.center.y, 125.0f, 1.0f);
}

TEST(MeasurementUnit, MeasureLineUsesMinAreaRect) {
    // Diagonal line as a contour. We test that the engine uses the
    // longer side of minAreaRect rather than the axis-aligned bbox.
    std::vector<cv::Point> contour;
    for (int t = 0; t <= 100; ++t) {
        contour.emplace_back(t, t);
        contour.emplace_back(t + 1, t);  // give it a tiny thickness so
                                         // minAreaRect is well-defined.
    }
    InspectionConfig cfg;
    cfg.pixelToMmRatio = 1.0;  // 1 px == 1 mm to keep numbers obvious.

    Measurement m;
    auto d = m.measureDefect(1, contour, cfg);
    // diag length ~ sqrt(100^2 + 100^2) ~ 141.4
    EXPECT_GT(d.lengthPx, 130.0);
    EXPECT_LT(d.lengthPx, 160.0);
    EXPECT_NEAR(d.lengthMm, d.lengthPx, 1e-6);
}
