#pragma once

#include <opencv2/core.hpp>

namespace mvi {

struct Defect {
    int id = 0;
    cv::Rect bbox;
    cv::Point2f center{0.0f, 0.0f};
    double areaPx = 0.0;
    double areaMm2 = 0.0;
    double lengthPx = 0.0;
    double lengthMm = 0.0;
};

}  // namespace mvi
