#include "Preprocessor.hpp"

#include <opencv2/imgproc.hpp>

namespace mvi {

cv::Mat Preprocessor::toGray(const cv::Mat& input) const {
    if (input.empty()) {
        return cv::Mat();
    }
    if (input.channels() == 1) {
        return input.clone();
    }
    cv::Mat gray;
    cv::cvtColor(input, gray, cv::COLOR_BGR2GRAY);
    return gray;
}

cv::Mat Preprocessor::applyCLAHE(const cv::Mat& gray) const {
    cv::Ptr<cv::CLAHE> clahe = cv::createCLAHE(2.0, cv::Size(8, 8));
    cv::Mat equalized;
    clahe->apply(gray, equalized);
    return equalized;
}

cv::Mat Preprocessor::denoise(const cv::Mat& gray) const {
    cv::Mat blurred;
    cv::GaussianBlur(gray, blurred, cv::Size(5, 5), 1.2);
    return blurred;
}

cv::Mat Preprocessor::thresholdImage(const cv::Mat& gray) const {
    // Combine Otsu and Canny so that we catch both blob-like defects (stains,
    // dots) and elongated edges (scratches). Each method alone misses one of
    // the two classes on real surface images.
    cv::Mat otsu;
    cv::threshold(gray, otsu, 0, 255,
                  cv::THRESH_BINARY_INV | cv::THRESH_OTSU);

    cv::Mat edges;
    cv::Canny(gray, edges, 50, 150);

    cv::Mat combined;
    cv::bitwise_or(otsu, edges, combined);

    // Morphological close fills small gaps inside scratch edges so contour
    // detection treats them as one defect instead of a dotted line.
    cv::Mat kernel = cv::getStructuringElement(cv::MORPH_ELLIPSE,
                                               cv::Size(3, 3));
    cv::morphologyEx(combined, combined, cv::MORPH_CLOSE, kernel);
    cv::morphologyEx(combined, combined, cv::MORPH_OPEN, kernel);
    return combined;
}

cv::Mat Preprocessor::preprocess(const cv::Mat& input) const {
    cv::Mat gray = toGray(input);
    if (gray.empty()) {
        return cv::Mat();
    }
    cv::Mat equalized = applyCLAHE(gray);
    cv::Mat smoothed = denoise(equalized);
    return thresholdImage(smoothed);
}

}  // namespace mvi
