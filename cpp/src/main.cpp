#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

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
        "                   [--min-contour-area-px <int>]\n"
        "                   [--adaptive-block-size <int>]  # odd, default 51\n"
        "                   [--adaptive-c <double>]        # default 10\n"
        "                   [--benchmark <N>]   # repeat the inspection N times\n"
        "                                       # and print timing statistics\n";
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
    int benchmarkRuns = 0;

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
        } else if (opt == "--adaptive-block-size") {
            if (!needsValue(i, argc, argv, opt)) return EXIT_FAILURE;
            cfg.adaptiveBlockSize = std::stoi(argv[i]);
        } else if (opt == "--adaptive-c") {
            if (!needsValue(i, argc, argv, opt)) return EXIT_FAILURE;
            cfg.adaptiveC = std::stod(argv[i]);
        } else if (opt == "--benchmark") {
            if (!needsValue(i, argc, argv, opt)) return EXIT_FAILURE;
            benchmarkRuns = std::stoi(argv[i]);
            if (benchmarkRuns <= 0) {
                std::cerr << "--benchmark requires N > 0\n";
                return EXIT_FAILURE;
            }
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

        if (benchmarkRuns > 0) {
            using clock = std::chrono::steady_clock;
            // Warm-up (first call hits OpenCV's lazy allocators) so the
            // reported numbers aren't skewed by one-off setup cost.
            engine.inspect(imagePath, outputDir, cfg);

            std::vector<double> samples;
            samples.reserve(static_cast<size_t>(benchmarkRuns));
            for (int i = 0; i < benchmarkRuns; ++i) {
                const auto t0 = clock::now();
                const auto r = engine.inspect(imagePath, outputDir, cfg);
                const auto t1 = clock::now();
                samples.push_back(
                    std::chrono::duration<double, std::milli>(t1 - t0).count());
                (void)r;  // silence unused-warning
            }
            std::sort(samples.begin(), samples.end());
            const double sum = std::accumulate(samples.begin(),
                                               samples.end(), 0.0);
            const double avg = sum / static_cast<double>(samples.size());
            const double minMs = samples.front();
            const double maxMs = samples.back();
            const double p50 = samples[samples.size() / 2];
            const double p95 = samples[static_cast<size_t>(
                samples.size() * 0.95)];

            std::cout << "benchmark"
                      << " runs=" << benchmarkRuns
                      << " image=" << imagePath
                      << " avg_ms=" << avg
                      << " min_ms=" << minMs
                      << " p50_ms=" << p50
                      << " p95_ms=" << p95
                      << " max_ms=" << maxMs
                      << " fps=" << (1000.0 / avg)
                      << "\n";
            return EXIT_SUCCESS;
        }

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
