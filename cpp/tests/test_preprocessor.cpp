#include <gtest/gtest.h>

#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>

#include "InspectionConfig.hpp"
#include "Preprocessor.hpp"

using mvi::InspectionConfig;
using mvi::Preprocessor;

TEST(PreprocessorUnit, ToGrayHandlesBgrAndPassesThroughGray) {
    Preprocessor pre;

    cv::Mat bgr(32, 32, CV_8UC3, cv::Scalar(50, 100, 200));
    cv::Mat gray = pre.toGray(bgr);
    EXPECT_EQ(gray.channels(), 1);
    EXPECT_EQ(gray.rows, 32);
    EXPECT_EQ(gray.cols, 32);

    cv::Mat already_gray(16, 16, CV_8UC1, cv::Scalar(123));
    cv::Mat passthrough = pre.toGray(already_gray);
    EXPECT_EQ(passthrough.channels(), 1);
    EXPECT_EQ(passthrough.size(), already_gray.size());
}

TEST(PreprocessorUnit, ToGrayOnEmptyReturnsEmpty) {
    Preprocessor pre;
    EXPECT_TRUE(pre.toGray(cv::Mat()).empty());
}

TEST(PreprocessorUnit, ApplyClaheKeepsShapeAndAmplifiesContrast) {
    Preprocessor pre;
    cv::Mat gray(128, 128, CV_8UC1);
    // Low-contrast random image clustered in [120, 135]. CLAHE stretches
    // each 8x8 tile's histogram to fill more of the dynamic range, so the
    // overall standard deviation should grow noticeably.
    cv::randu(gray, cv::Scalar(120), cv::Scalar(135));
    cv::Mat out = pre.applyCLAHE(gray);
    EXPECT_EQ(out.size(), gray.size());
    EXPECT_EQ(out.channels(), 1);

    cv::Scalar inStd, outStd;
    cv::meanStdDev(gray, cv::Scalar(), inStd);
    cv::meanStdDev(out, cv::Scalar(), outStd);
    EXPECT_GT(outStd[0], inStd[0] * 2.0)
        << "CLAHE on a low-contrast image should at least double the std.";
}

TEST(PreprocessorUnit, DenoiseLowersHighFrequencyNoise) {
    Preprocessor pre;
    cv::Mat gray(64, 64, CV_8UC1);
    cv::randu(gray, 100, 200);
    cv::Mat smoothed = pre.denoise(gray);
    EXPECT_EQ(smoothed.size(), gray.size());

    cv::Scalar inStd, outStd;
    cv::meanStdDev(gray, cv::Scalar(), inStd);
    cv::meanStdDev(smoothed, cv::Scalar(), outStd);
    // Gaussian blur with sigma=1.2 should noticeably reduce the std of a
    // uniformly random grey image.
    EXPECT_LT(outStd[0], inStd[0]);
}

TEST(PreprocessorUnit, ThresholdOnFlatSurfaceProducesAlmostNoForeground) {
    Preprocessor pre;
    cv::Mat flat(256, 256, CV_8UC1, cv::Scalar(180));
    cv::Mat bin = pre.thresholdImage(flat);
    EXPECT_EQ(bin.size(), flat.size());
    EXPECT_EQ(bin.channels(), 1);
    const double fg_ratio = cv::countNonZero(bin) /
                            static_cast<double>(bin.total());
    EXPECT_LT(fg_ratio, 0.02)
        << "Adaptive threshold on a perfectly flat surface should leave "
           "almost no foreground (Otsu would fail this test).";
}

TEST(PreprocessorUnit, ThresholdDetectsDarkBlob) {
    Preprocessor pre;
    cv::Mat gray(256, 256, CV_8UC1, cv::Scalar(190));
    // Place a clearly dark blob at the centre.
    cv::circle(gray, cv::Point(128, 128), 20, cv::Scalar(40), -1);
    cv::Mat bin = pre.thresholdImage(gray);

    // Some pixels inside the blob region should be marked foreground.
    cv::Mat roi = bin(cv::Rect(108, 108, 40, 40));
    const int fg_in_roi = cv::countNonZero(roi);
    EXPECT_GT(fg_in_roi, 100)
        << "A 40-grey circle on a 190-grey surface should produce a clearly "
           "visible foreground blob.";
}

TEST(PreprocessorUnit, PreprocessRoutesAdaptiveKnobsFromConfig) {
    Preprocessor pre;
    cv::Mat gray(256, 256, CV_8UC1, cv::Scalar(180));
    cv::circle(gray, cv::Point(128, 128), 10, cv::Scalar(150), -1);
    cv::Mat bgr;
    cv::cvtColor(gray, bgr, cv::COLOR_GRAY2BGR);

    InspectionConfig lenient;
    lenient.adaptiveC = 5.0;  // small C -> sensitive

    InspectionConfig strict;
    strict.adaptiveC = 50.0;  // large C -> only very dark blobs trip it

    const int fg_lenient = cv::countNonZero(pre.preprocess(bgr, lenient));
    const int fg_strict = cv::countNonZero(pre.preprocess(bgr, strict));
    EXPECT_GT(fg_lenient, fg_strict)
        << "Lower adaptiveC must flag at least as many pixels as a higher C "
           "on the same image; otherwise the knob is not being routed.";
}
