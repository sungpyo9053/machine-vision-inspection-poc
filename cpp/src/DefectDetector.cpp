#include "DefectDetector.hpp"

#include <opencv2/imgproc.hpp>

namespace mvi {

std::vector<std::vector<cv::Point>> DefectDetector::findContours(
    const cv::Mat& binary) const {
    std::vector<std::vector<cv::Point>> contours;
    if (binary.empty()) {
        return contours;
    }
    cv::findContours(binary, contours, cv::RETR_EXTERNAL,
                     cv::CHAIN_APPROX_SIMPLE);
    return contours;
}

std::vector<std::vector<cv::Point>> DefectDetector::filterNoise(
    const std::vector<std::vector<cv::Point>>& contours,
    int minAreaPx) const {
    std::vector<std::vector<cv::Point>> filtered;
    filtered.reserve(contours.size());
    for (const auto& c : contours) {
        const double area = cv::contourArea(c);
        if (area >= static_cast<double>(minAreaPx)) {
            filtered.push_back(c);
        }
    }
    return filtered;
}

std::vector<std::vector<cv::Point>> DefectDetector::detect(
    const cv::Mat& binary, const InspectionConfig& cfg) const {
    auto contours = findContours(binary);
    return filterNoise(contours, cfg.minContourAreaPx);
}

}  // namespace mvi
