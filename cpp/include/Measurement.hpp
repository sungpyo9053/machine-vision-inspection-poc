#pragma once

#include <vector>

#include <opencv2/core.hpp>

#include "Defect.hpp"
#include "InspectionConfig.hpp"

namespace mvi {

class Measurement {
public:
    Defect measureDefect(int id,
                         const std::vector<cv::Point>& contour,
                         const InspectionConfig& cfg) const;

    double pxToMm(double px, double pixelToMmRatio) const;
    double pxAreaToMm2(double areaPx, double pixelToMmRatio) const;
};

}  // namespace mvi
