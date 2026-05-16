#include "ReportWriter.hpp"

#include <filesystem>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <stdexcept>

#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>

namespace fs = std::filesystem;

namespace mvi {

namespace {

void ensureDir(const std::string& dir) {
    if (dir.empty()) {
        return;
    }
    std::error_code ec;
    fs::create_directories(dir, ec);
    if (ec) {
        throw std::runtime_error("Failed to create output directory: " + dir +
                                 " (" + ec.message() + ")");
    }
}

std::string joinPath(const std::string& dir, const std::string& file) {
    if (dir.empty()) return file;
    fs::path p(dir);
    p /= file;
    return p.string();
}

// Minimal hand-rolled JSON escaping. We control the field set, so we only need
// to escape backslash, quote, and the common control characters.
std::string jsonEscape(const std::string& s) {
    std::string out;
    out.reserve(s.size() + 2);
    for (char c : s) {
        switch (c) {
            case '"':  out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if (static_cast<unsigned char>(c) < 0x20) {
                    char buf[8];
                    std::snprintf(buf, sizeof(buf), "\\u%04x",
                                  static_cast<unsigned>(c));
                    out += buf;
                } else {
                    out += c;
                }
        }
    }
    return out;
}

std::string num(double v) {
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(4) << v;
    return oss.str();
}

}  // namespace

std::string ReportWriter::saveResultImage(const cv::Mat& originalBgr,
                                          const InspectionResult& result,
                                          const std::string& outputDir) const {
    ensureDir(outputDir);
    cv::Mat overlay = originalBgr.clone();

    const cv::Scalar okColor(0, 200, 0);
    const cv::Scalar ngColor(0, 0, 230);
    const cv::Scalar color = (result.result == "OK") ? okColor : ngColor;

    for (const auto& d : result.defects) {
        cv::rectangle(overlay, d.bbox, color, 2);
        std::ostringstream tag;
        tag << "#" << d.id << " " << std::fixed << std::setprecision(2)
            << d.areaMm2 << "mm^2";
        cv::Point textOrg(d.bbox.x, std::max(15, d.bbox.y - 5));
        cv::putText(overlay, tag.str(), textOrg, cv::FONT_HERSHEY_SIMPLEX,
                    0.5, color, 1, cv::LINE_AA);
    }

    std::ostringstream banner;
    banner << result.result << "  defects=" << result.defectCount;
    cv::putText(overlay, banner.str(), cv::Point(15, 30),
                cv::FONT_HERSHEY_SIMPLEX, 0.9, color, 2, cv::LINE_AA);

    const std::string outPath =
        joinPath(outputDir, "result_" + result.imageName + ".png");
    if (!cv::imwrite(outPath, overlay)) {
        throw std::runtime_error("Failed to write result image: " + outPath);
    }
    return outPath;
}

std::string ReportWriter::saveJsonReport(const InspectionResult& result,
                                         const InspectionConfig& cfg,
                                         const std::string& outputDir) const {
    ensureDir(outputDir);
    const std::string outPath =
        joinPath(outputDir, "inspection_report_" + result.imageName + ".json");

    std::ostringstream o;
    o << "{\n";
    o << "  \"image_name\": \"" << jsonEscape(result.imageName) << "\",\n";
    o << "  \"result\": \"" << result.result << "\",\n";
    o << "  \"defect_count\": " << result.defectCount << ",\n";
    o << "  \"max_area_mm2\": " << num(result.maxAreaMm2) << ",\n";
    o << "  \"max_length_mm\": " << num(result.maxLengthMm) << ",\n";
    o << "  \"total_area_mm2\": " << num(result.totalAreaMm2) << ",\n";
    o << "  \"created_at\": \"" << result.createdAt << "\",\n";
    o << "  \"result_image_path\": \"" << jsonEscape(result.resultImagePath)
      << "\",\n";
    o << "  \"config\": {\n";
    o << "    \"pixel_to_mm_ratio\": " << num(cfg.pixelToMmRatio) << ",\n";
    o << "    \"min_contour_area_px\": " << cfg.minContourAreaPx << ",\n";
    o << "    \"max_defect_count\": " << cfg.maxDefectCount << ",\n";
    o << "    \"max_defect_area_mm2\": " << num(cfg.maxDefectAreaMm2) << ",\n";
    o << "    \"max_defect_length_mm\": " << num(cfg.maxDefectLengthMm) << "\n";
    o << "  },\n";
    o << "  \"defects\": [";
    for (size_t i = 0; i < result.defects.size(); ++i) {
        const auto& d = result.defects[i];
        if (i == 0) o << "\n";
        o << "    {\n";
        o << "      \"defect_id\": " << d.id << ",\n";
        o << "      \"bbox\": {\"x\": " << d.bbox.x << ", \"y\": " << d.bbox.y
          << ", \"w\": " << d.bbox.width << ", \"h\": " << d.bbox.height
          << "},\n";
        o << "      \"center\": {\"x\": " << num(d.center.x) << ", \"y\": "
          << num(d.center.y) << "},\n";
        o << "      \"area_px\": " << num(d.areaPx) << ",\n";
        o << "      \"area_mm2\": " << num(d.areaMm2) << ",\n";
        o << "      \"length_px\": " << num(d.lengthPx) << ",\n";
        o << "      \"length_mm\": " << num(d.lengthMm) << "\n";
        o << "    }" << (i + 1 < result.defects.size() ? "," : "") << "\n";
    }
    o << "  ]\n";
    o << "}\n";

    std::ofstream ofs(outPath);
    if (!ofs) {
        throw std::runtime_error("Failed to open JSON report for write: " +
                                 outPath);
    }
    ofs << o.str();
    return outPath;
}

void ReportWriter::appendCsv(const InspectionResult& result,
                             const std::string& outputDir) const {
    ensureDir(outputDir);
    const std::string outPath = joinPath(outputDir, "inspection_results.csv");

    const bool exists = fs::exists(outPath);
    std::ofstream ofs(outPath, std::ios::app);
    if (!ofs) {
        throw std::runtime_error("Failed to open CSV for append: " + outPath);
    }
    if (!exists) {
        ofs << "image_name,result,defect_count,max_area_mm2,max_length_mm,"
               "total_area_mm2,created_at\n";
    }
    ofs << result.imageName << ',' << result.result << ','
        << result.defectCount << ',' << num(result.maxAreaMm2) << ','
        << num(result.maxLengthMm) << ',' << num(result.totalAreaMm2) << ','
        << result.createdAt << '\n';
}

}  // namespace mvi
