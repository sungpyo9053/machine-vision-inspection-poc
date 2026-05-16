#include "InspectionEngine.hpp"

#include <algorithm>
#include <chrono>
#include <ctime>
#include <iomanip>
#include <sstream>
#include <stdexcept>

#include <opencv2/imgcodecs.hpp>

#include "DefectDetector.hpp"
#include "Measurement.hpp"
#include "Preprocessor.hpp"
#include "ReportWriter.hpp"

namespace mvi {

namespace {

std::string baseNameNoExt(const std::string& path) {
    auto slash = path.find_last_of("/\\");
    std::string file = (slash == std::string::npos) ? path : path.substr(slash + 1);
    auto dot = file.find_last_of('.');
    return (dot == std::string::npos) ? file : file.substr(0, dot);
}

std::string currentTimestamp() {
    using clock = std::chrono::system_clock;
    const auto now = clock::now();
    const std::time_t t = clock::to_time_t(now);
    std::tm tm{};
#if defined(_WIN32)
    localtime_s(&tm, &t);
#else
    localtime_r(&t, &tm);
#endif
    std::ostringstream oss;
    oss << std::put_time(&tm, "%Y-%m-%dT%H:%M:%S");
    return oss.str();
}

}  // namespace

std::string InspectionEngine::verdict(int defectCount,
                                      double maxAreaMm2,
                                      double maxLengthMm,
                                      const InspectionConfig& cfg) {
    if (defectCount > cfg.maxDefectCount) return "NG";
    if (maxAreaMm2 > cfg.maxDefectAreaMm2) return "NG";
    if (maxLengthMm > cfg.maxDefectLengthMm) return "NG";
    return "OK";
}

InspectionResult InspectionEngine::inspect(const std::string& imagePath,
                                           const std::string& outputDir,
                                           const InspectionConfig& cfg) const {
    cv::Mat input = cv::imread(imagePath, cv::IMREAD_UNCHANGED);
    if (input.empty()) {
        throw std::runtime_error("Failed to load image: " + imagePath);
    }

    cv::Mat bgr;
    if (input.channels() == 1) {
        cv::cvtColor(input, bgr, cv::COLOR_GRAY2BGR);
    } else if (input.channels() == 4) {
        cv::cvtColor(input, bgr, cv::COLOR_BGRA2BGR);
    } else {
        bgr = input;
    }

    Preprocessor pre;
    cv::Mat binary = pre.preprocess(bgr);

    DefectDetector detector;
    auto contours = detector.detect(binary, cfg);

    Measurement meas;
    InspectionResult result;
    result.imageName = baseNameNoExt(imagePath);
    result.createdAt = currentTimestamp();

    int nextId = 1;
    for (const auto& c : contours) {
        Defect d = meas.measureDefect(nextId++, c, cfg);
        result.totalAreaMm2 += d.areaMm2;
        result.maxAreaMm2 = std::max(result.maxAreaMm2, d.areaMm2);
        result.maxLengthMm = std::max(result.maxLengthMm, d.lengthMm);
        result.defects.push_back(std::move(d));
    }
    result.defectCount = static_cast<int>(result.defects.size());
    result.result = verdict(result.defectCount, result.maxAreaMm2,
                            result.maxLengthMm, cfg);

    ReportWriter writer;
    result.resultImagePath = writer.saveResultImage(bgr, result, outputDir);
    result.jsonReportPath = writer.saveJsonReport(result, cfg, outputDir);
    writer.appendCsv(result, outputDir);

    return result;
}

}  // namespace mvi
