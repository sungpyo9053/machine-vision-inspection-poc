#pragma once

#include <string>

#include "InspectionConfig.hpp"
#include "InspectionResult.hpp"

namespace mvi {

class InspectionEngine {
public:
    InspectionResult inspect(const std::string& imagePath,
                             const std::string& outputDir,
                             const InspectionConfig& cfg) const;
};

}  // namespace mvi
