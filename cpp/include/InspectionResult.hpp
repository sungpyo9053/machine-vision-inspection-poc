#pragma once

#include <string>
#include <vector>

#include "Defect.hpp"

namespace mvi {

struct InspectionResult {
    std::string imageName;
    std::string result;  // "OK" or "NG"
    int defectCount = 0;
    double maxAreaMm2 = 0.0;
    double maxLengthMm = 0.0;
    double totalAreaMm2 = 0.0;
    std::vector<Defect> defects;
    std::string createdAt;
    std::string resultImagePath;
    std::string jsonReportPath;
};

}  // namespace mvi
