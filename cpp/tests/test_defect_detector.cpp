#include <gtest/gtest.h>

#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>

#include "DefectDetector.hpp"
#include "InspectionConfig.hpp"

using mvi::DefectDetector;
using mvi::InspectionConfig;

namespace {

cv::Mat makeBinaryWithBlobs(const std::vector<cv::Rect>& blobs,
                            int rows = 256, int cols = 256) {
    cv::Mat bin(rows, cols, CV_8UC1, cv::Scalar(0));
    for (const auto& r : blobs) {
        cv::rectangle(bin, r, cv::Scalar(255), cv::FILLED);
    }
    return bin;
}

}  // namespace

TEST(DefectDetectorUnit, FindContoursOnEmptyImageReturnsEmpty) {
    DefectDetector det;
    cv::Mat empty;
    EXPECT_TRUE(det.findContours(empty).empty());
}

TEST(DefectDetectorUnit, FindContoursOnBlackImageReturnsEmpty) {
    DefectDetector det;
    cv::Mat black(64, 64, CV_8UC1, cv::Scalar(0));
    EXPECT_TRUE(det.findContours(black).empty());
}

TEST(DefectDetectorUnit, FindContoursOnTwoSeparateBlobs) {
    DefectDetector det;
    cv::Mat bin = makeBinaryWithBlobs({
        cv::Rect(10, 10, 30, 30),
        cv::Rect(100, 100, 20, 20),
    });
    auto contours = det.findContours(bin);
    EXPECT_EQ(contours.size(), 2u);
}

TEST(DefectDetectorUnit, FilterNoiseDropsSmallContours) {
    DefectDetector det;
    // 30x30 blob -> ~900 px²; 4x4 blob -> ~16 px²
    cv::Mat bin = makeBinaryWithBlobs({
        cv::Rect(10, 10, 30, 30),
        cv::Rect(100, 100, 4, 4),
    });
    auto raw = det.findContours(bin);
    ASSERT_EQ(raw.size(), 2u);
    auto kept = det.filterNoise(raw, /*minAreaPx=*/100);
    EXPECT_EQ(kept.size(), 1u)
        << "filterNoise with minAreaPx=100 should drop the 16-px blob and "
           "keep the 900-px blob.";
}

TEST(DefectDetectorUnit, FilterNoiseKeepsEverythingWhenThresholdIsZero) {
    DefectDetector det;
    cv::Mat bin = makeBinaryWithBlobs({
        cv::Rect(10, 10, 5, 5),
        cv::Rect(40, 40, 5, 5),
        cv::Rect(80, 80, 5, 5),
    });
    auto raw = det.findContours(bin);
    auto kept = det.filterNoise(raw, /*minAreaPx=*/0);
    EXPECT_EQ(kept.size(), raw.size());
}

TEST(DefectDetectorUnit, DetectUsesConfigMinArea) {
    DefectDetector det;
    // cv::contourArea uses Green's theorem on the polygon vertices, so a
    // WxH filled rectangle reads as (W-1) * (H-1), not W * H. Pick sizes
    // that are unambiguous on both sides of the thresholds we test.
    cv::Mat bin = makeBinaryWithBlobs({
        cv::Rect(10, 10, 30, 30),   // shoelace area ~ 841  -> always kept
        cv::Rect(60, 60, 10, 10),   // shoelace area ~ 81   -> kept >=30, dropped >=100
    });
    InspectionConfig cfg;
    cfg.minContourAreaPx = 30;
    auto kept30 = det.detect(bin, cfg);
    EXPECT_EQ(kept30.size(), 2u);

    cfg.minContourAreaPx = 100;
    auto kept100 = det.detect(bin, cfg);
    EXPECT_EQ(kept100.size(), 1u);
}

TEST(DefectDetectorUnit, RetrievesOnlyOuterContours) {
    DefectDetector det;
    // Outer 40x40 blob with a 20x20 hole inside. RETR_EXTERNAL must return
    // exactly one contour, not two.
    cv::Mat bin(128, 128, CV_8UC1, cv::Scalar(0));
    cv::rectangle(bin, cv::Rect(40, 40, 40, 40), cv::Scalar(255), cv::FILLED);
    cv::rectangle(bin, cv::Rect(50, 50, 20, 20), cv::Scalar(0), cv::FILLED);
    auto contours = det.findContours(bin);
    EXPECT_EQ(contours.size(), 1u);
}
