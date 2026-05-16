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

    // Exposed for unit tests. Decides OK/NG from already-measured aggregate
    // values + the threshold config. Order of checks is documented in
    // docs/inspection_algorithm.md.
    static std::string verdict(int defectCount,
                               double maxAreaMm2,
                               double maxLengthMm,
                               const InspectionConfig& cfg);
};

}  // namespace mvi
