#include <gtest/gtest.h>

#include <cstdio>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>

#include <opencv2/core.hpp>

#include "InspectionConfig.hpp"
#include "InspectionResult.hpp"
#include "ReportWriter.hpp"

namespace fs = std::filesystem;

using mvi::Defect;
using mvi::InspectionConfig;
using mvi::InspectionResult;
using mvi::ReportWriter;

namespace {

std::string slurp(const std::string& path) {
    std::ifstream ifs(path);
    std::ostringstream ss;
    ss << ifs.rdbuf();
    return ss.str();
}

InspectionResult sampleResult() {
    InspectionResult r;
    r.imageName = "demo";
    r.result = "NG";
    r.defectCount = 2;
    r.maxAreaMm2 = 1.23;
    r.maxLengthMm = 4.56;
    r.totalAreaMm2 = 1.7;
    r.createdAt = "2026-05-16T09:00:00";

    Defect a;
    a.id = 1;
    a.bbox = cv::Rect(10, 20, 30, 40);
    a.center = cv::Point2f(25.0f, 40.0f);
    a.areaPx = 320.0;
    a.areaMm2 = 0.8;
    a.lengthPx = 51.2;
    a.lengthMm = 2.56;
    r.defects.push_back(a);

    Defect b;
    b.id = 2;
    b.bbox = cv::Rect(80, 90, 12, 14);
    b.center = cv::Point2f(86.0f, 97.0f);
    b.areaPx = 100.0;
    b.areaMm2 = 0.25;
    b.lengthPx = 21.0;
    b.lengthMm = 1.05;
    r.defects.push_back(b);

    return r;
}

}  // namespace

TEST(ReportWriterUnit, JsonContainsRequiredFields) {
    auto tmp = fs::temp_directory_path() / "vi_test_json";
    fs::remove_all(tmp);

    ReportWriter w;
    auto result = sampleResult();
    InspectionConfig cfg;
    cfg.pixelToMmRatio = 0.05;
    cfg.maxDefectCount = 3;
    cfg.maxDefectAreaMm2 = 2.0;
    cfg.maxDefectLengthMm = 5.0;

    const auto jsonPath = w.saveJsonReport(result, cfg, tmp.string());
    ASSERT_TRUE(fs::exists(jsonPath));

    const auto body = slurp(jsonPath);
    EXPECT_NE(body.find("\"image_name\": \"demo\""), std::string::npos);
    EXPECT_NE(body.find("\"result\": \"NG\""), std::string::npos);
    EXPECT_NE(body.find("\"defect_count\": 2"), std::string::npos);
    EXPECT_NE(body.find("\"defect_id\": 1"), std::string::npos);
    EXPECT_NE(body.find("\"defect_id\": 2"), std::string::npos);
    EXPECT_NE(body.find("\"area_mm2\": 0.8000"), std::string::npos);
    EXPECT_NE(body.find("\"length_mm\": 2.5600"), std::string::npos);
    EXPECT_NE(body.find("\"config\":"), std::string::npos);

    fs::remove_all(tmp);
}

TEST(ReportWriterUnit, CsvAppendsAndKeepsHeaderOnce) {
    auto tmp = fs::temp_directory_path() / "vi_test_csv";
    fs::remove_all(tmp);

    ReportWriter w;
    auto r = sampleResult();
    w.appendCsv(r, tmp.string());
    w.appendCsv(r, tmp.string());
    w.appendCsv(r, tmp.string());

    const auto csv = slurp((tmp / "inspection_results.csv").string());
    const auto firstNewline = csv.find('\n');
    ASSERT_NE(firstNewline, std::string::npos);
    const auto header = csv.substr(0, firstNewline);
    EXPECT_NE(header.find("image_name"), std::string::npos);
    EXPECT_NE(header.find("result"), std::string::npos);
    EXPECT_NE(header.find("created_at"), std::string::npos);

    // 3 data rows + 1 header
    size_t rows = 0;
    for (char c : csv) if (c == '\n') ++rows;
    EXPECT_EQ(rows, 4u);

    fs::remove_all(tmp);
}

TEST(ReportWriterUnit, JsonEscapesBackslashAndQuote) {
    auto tmp = fs::temp_directory_path() / "vi_test_json_esc";
    fs::remove_all(tmp);

    ReportWriter w;
    auto r = sampleResult();
    r.imageName = "weird\"name\\with-slashes";
    InspectionConfig cfg;

    const auto jsonPath = w.saveJsonReport(r, cfg, tmp.string());
    const auto body = slurp(jsonPath);
    // Quote and backslash must be escaped; raw characters should not appear
    // outside the escaped form.
    EXPECT_NE(body.find("weird\\\"name\\\\with-slashes"), std::string::npos);
    fs::remove_all(tmp);
}
