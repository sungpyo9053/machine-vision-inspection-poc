#include <gtest/gtest.h>

#include "InspectionConfig.hpp"
#include "InspectionEngine.hpp"

using mvi::InspectionConfig;
using mvi::InspectionEngine;

TEST(VerdictUnit, AllUnderThresholdReturnsOk) {
    InspectionConfig cfg;
    cfg.maxDefectCount = 3;
    cfg.maxDefectAreaMm2 = 2.0;
    cfg.maxDefectLengthMm = 5.0;
    EXPECT_EQ(InspectionEngine::verdict(0, 0.0, 0.0, cfg), "OK");
    EXPECT_EQ(InspectionEngine::verdict(3, 2.0, 5.0, cfg), "OK");
    EXPECT_EQ(InspectionEngine::verdict(1, 0.5, 1.2, cfg), "OK");
}

TEST(VerdictUnit, ExceedingCountTripsNg) {
    InspectionConfig cfg;
    cfg.maxDefectCount = 3;
    cfg.maxDefectAreaMm2 = 2.0;
    cfg.maxDefectLengthMm = 5.0;
    EXPECT_EQ(InspectionEngine::verdict(4, 0.0, 0.0, cfg), "NG");
}

TEST(VerdictUnit, ExceedingAreaTripsNg) {
    InspectionConfig cfg;
    cfg.maxDefectCount = 3;
    cfg.maxDefectAreaMm2 = 2.0;
    cfg.maxDefectLengthMm = 5.0;
    EXPECT_EQ(InspectionEngine::verdict(1, 2.0001, 0.0, cfg), "NG");
}

TEST(VerdictUnit, ExceedingLengthTripsNg) {
    InspectionConfig cfg;
    cfg.maxDefectCount = 3;
    cfg.maxDefectAreaMm2 = 2.0;
    cfg.maxDefectLengthMm = 5.0;
    EXPECT_EQ(InspectionEngine::verdict(1, 0.0, 5.0001, cfg), "NG");
}

TEST(VerdictUnit, BoundaryIsOkNotNg) {
    // Spec: condition is strictly greater than threshold. Hitting the
    // threshold exactly stays OK so tuning is symmetric.
    InspectionConfig cfg;
    cfg.maxDefectCount = 3;
    cfg.maxDefectAreaMm2 = 2.0;
    cfg.maxDefectLengthMm = 5.0;
    EXPECT_EQ(InspectionEngine::verdict(3, 2.0, 5.0, cfg), "OK");
}
