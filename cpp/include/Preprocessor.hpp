#pragma once

#include <opencv2/core.hpp>

#include "InspectionConfig.hpp"

namespace mvi {

// Image preprocessing pipeline. Each step is exposed individually so that the
// design doc can refer to it, but `preprocess()` is the only entry point the
// engine uses.
class Preprocessor {
public:
    // The engine routes its InspectionConfig through here so the adaptive
    // threshold knobs (blockSize, C) can be tuned per surface without a
    // rebuild. Default-constructed config reproduces the original behaviour.
    cv::Mat preprocess(const cv::Mat& input,
                       const InspectionConfig& cfg = InspectionConfig{}) const;

    cv::Mat toGray(const cv::Mat& input) const;
    cv::Mat applyCLAHE(const cv::Mat& gray) const;
    cv::Mat denoise(const cv::Mat& gray) const;
    cv::Mat thresholdImage(const cv::Mat& gray,
                           const InspectionConfig& cfg = InspectionConfig{}) const;
};

}  // namespace mvi
