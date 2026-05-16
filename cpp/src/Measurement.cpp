#include "Measurement.hpp"

#include <algorithm>
#include <cmath>

#include <opencv2/imgproc.hpp>

namespace mvi {

double Measurement::pxToMm(double px, double pixelToMmRatio) const {
    return px * pixelToMmRatio;
}

double Measurement::pxAreaToMm2(double areaPx, double pixelToMmRatio) const {
    return areaPx * pixelToMmRatio * pixelToMmRatio;
}

Defect Measurement::measureDefect(int id,
                                  const std::vector<cv::Point>& contour,
                                  const InspectionConfig& cfg) const {
    Defect d;
    d.id = id;
    d.bbox = cv::boundingRect(contour);
    d.areaPx = cv::contourArea(contour);

    // Use the minimum enclosing rotated rectangle's longer side as the
    // characteristic length. This matches scratch length better than the
    // axis-aligned bounding box for diagonal defects.
    if (contour.size() >= 3) {
        cv::RotatedRect rr = cv::minAreaRect(contour);
        d.lengthPx = std::max(rr.size.width, rr.size.height);
    } else {
        d.lengthPx = std::max(d.bbox.width, d.bbox.height);
    }

    cv::Moments m = cv::moments(contour);
    if (m.m00 > 1e-6) {
        d.center = cv::Point2f(static_cast<float>(m.m10 / m.m00),
                               static_cast<float>(m.m01 / m.m00));
    } else {
        d.center = cv::Point2f(static_cast<float>(d.bbox.x + d.bbox.width / 2.0),
                               static_cast<float>(d.bbox.y + d.bbox.height / 2.0));
    }

    d.areaMm2 = pxAreaToMm2(d.areaPx, cfg.pixelToMmRatio);
    d.lengthMm = pxToMm(d.lengthPx, cfg.pixelToMmRatio);
    return d;
}

}  // namespace mvi
