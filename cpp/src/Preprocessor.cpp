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
    // Adaptive threshold: a pixel is foreground only if it is meaningfully
    // (>= 10 gray levels) darker than its local 51x51 neighbourhood mean.
    //
    // Why not Otsu: Otsu always picks SOME threshold, even when the image
    // contains no defects. On a flat surface with mild lighting non-uniformity
    // it tends to split the image in half and flag the dark half as one giant
    // foreground blob, producing a phantom NG result. Adaptive thresholding
    // self-cancels under uniform illumination because the local mean tracks
    // the surface itself, so flat areas produce no foreground.
    //
    // Canny edges still feed in so that thin scratches -- whose interior is
    // not particularly darker than the local mean -- are caught via the edge
    // response and then closed into a single contour.
    cv::Mat darkBlobs;
    cv::adaptiveThreshold(gray, darkBlobs, 255,
                          cv::ADAPTIVE_THRESH_GAUSSIAN_C,
                          cv::THRESH_BINARY_INV,
                          51, 10);

    cv::Mat edges;
    cv::Canny(gray, edges, 50, 150);

    cv::Mat combined;
    cv::bitwise_or(darkBlobs, edges, combined);

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
