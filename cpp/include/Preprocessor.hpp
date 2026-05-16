#pragma once

#include <opencv2/core.hpp>

namespace mvi {

// Image preprocessing pipeline. Each step is exposed individually so that the
// design doc can refer to it, but `preprocess()` is the only entry point the
// engine uses.
class Preprocessor {
public:
    cv::Mat preprocess(const cv::Mat& input) const;

    cv::Mat toGray(const cv::Mat& input) const;
    cv::Mat applyCLAHE(const cv::Mat& gray) const;
    cv::Mat denoise(const cv::Mat& gray) const;
    cv::Mat thresholdImage(const cv::Mat& gray) const;
};

}  // namespace mvi
