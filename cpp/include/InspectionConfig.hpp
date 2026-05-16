#pragma once

namespace mvi {

struct InspectionConfig {
    double pixelToMmRatio = 0.05;
    int minContourAreaPx = 30;
    int maxDefectCount = 3;
    double maxDefectAreaMm2 = 2.0;
    double maxDefectLengthMm = 5.0;
};

}  // namespace mvi
