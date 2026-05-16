#pragma once

#include <string>

#include <opencv2/core.hpp>

#include "InspectionConfig.hpp"
#include "InspectionResult.hpp"

namespace mvi {

class ReportWriter {
public:
    std::string saveResultImage(const cv::Mat& originalBgr,
                                const InspectionResult& result,
                                const std::string& outputDir) const;

    std::string saveJsonReport(const InspectionResult& result,
                               const InspectionConfig& cfg,
                               const std::string& outputDir) const;

    void appendCsv(const InspectionResult& result,
                   const std::string& outputDir) const;
};

}  // namespace mvi
