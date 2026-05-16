#include <cstdlib>
#include <iostream>
#include <string>

#include "InspectionConfig.hpp"
#include "InspectionEngine.hpp"
#include "InspectionResult.hpp"

namespace {

void printUsage() {
    std::cout <<
        "Usage:\n"
        "  vision_inspector --image <image_path> --output <output_dir>\n"
        "                   [--pixel-to-mm <double>]\n"
        "                   [--max-defect-count <int>]\n"
        "                   [--max-defect-area-mm2 <double>]\n"
        "                   [--max-defect-length-mm <double>]\n"
        "                   [--min-contour-area-px <int>]\n";
}

bool needsValue(int& i, int argc, char** argv, const std::string& opt) {
    if (i + 1 >= argc) {
        std::cerr << "Missing value for " << opt << "\n";
        return false;
    }
    ++i;
    return true;
}

}  // namespace

int main(int argc, char** argv) {
    std::string imagePath;
    std::string outputDir = "data/results";
    mvi::InspectionConfig cfg;

    for (int i = 1; i < argc; ++i) {
        const std::string opt = argv[i];
        if (opt == "--image") {
            if (!needsValue(i, argc, argv, opt)) return EXIT_FAILURE;
            imagePath = argv[i];
        } else if (opt == "--output") {
            if (!needsValue(i, argc, argv, opt)) return EXIT_FAILURE;
            outputDir = argv[i];
        } else if (opt == "--pixel-to-mm") {
            if (!needsValue(i, argc, argv, opt)) return EXIT_FAILURE;
            cfg.pixelToMmRatio = std::stod(argv[i]);
        } else if (opt == "--max-defect-count") {
            if (!needsValue(i, argc, argv, opt)) return EXIT_FAILURE;
            cfg.maxDefectCount = std::stoi(argv[i]);
        } else if (opt == "--max-defect-area-mm2") {
            if (!needsValue(i, argc, argv, opt)) return EXIT_FAILURE;
            cfg.maxDefectAreaMm2 = std::stod(argv[i]);
        } else if (opt == "--max-defect-length-mm") {
            if (!needsValue(i, argc, argv, opt)) return EXIT_FAILURE;
            cfg.maxDefectLengthMm = std::stod(argv[i]);
        } else if (opt == "--min-contour-area-px") {
            if (!needsValue(i, argc, argv, opt)) return EXIT_FAILURE;
            cfg.minContourAreaPx = std::stoi(argv[i]);
        } else if (opt == "--help" || opt == "-h") {
            printUsage();
            return EXIT_SUCCESS;
        } else {
            std::cerr << "Unknown option: " << opt << "\n";
            printUsage();
            return EXIT_FAILURE;
        }
    }

    if (imagePath.empty()) {
        std::cerr << "Error: --image is required\n";
        printUsage();
        return EXIT_FAILURE;
    }

    try {
        mvi::InspectionEngine engine;
        const auto result = engine.inspect(imagePath, outputDir, cfg);
        std::cout << "image=" << result.imageName
                  << " result=" << result.result
                  << " defect_count=" << result.defectCount
                  << " max_area_mm2=" << result.maxAreaMm2
                  << " max_length_mm=" << result.maxLengthMm
                  << " total_area_mm2=" << result.totalAreaMm2
                  << " json=" << result.jsonReportPath
                  << " result_image=" << result.resultImagePath
                  << "\n";
    } catch (const std::exception& e) {
        std::cerr << "Inspection failed: " << e.what() << "\n";
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
