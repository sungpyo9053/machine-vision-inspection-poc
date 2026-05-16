#pragma once

#include <vector>

#include <opencv2/core.hpp>

#include "InspectionConfig.hpp"

namespace mvi {

class DefectDetector {
public:
    // Returns contours that look like real defects (noise filtered out).
    // `binary` is expected to be an 8-bit single channel mask where foreground
    // (255) marks defect candidates.
    std::vector<std::vector<cv::Point>> detect(const cv::Mat& binary,
                                               const InspectionConfig& cfg) const;

    std::vector<std::vector<cv::Point>> findContours(const cv::Mat& binary) const;

    std::vector<std::vector<cv::Point>> filterNoise(
        const std::vector<std::vector<cv::Point>>& contours,
        int minAreaPx) const;
};

}  // namespace mvi
