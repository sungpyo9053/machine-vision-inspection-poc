#pragma once

namespace mvi {

struct InspectionConfig {
    double pixelToMmRatio = 0.05;
    int minContourAreaPx = 30;
    int maxDefectCount = 3;
    double maxDefectAreaMm2 = 2.0;
    double maxDefectLengthMm = 5.0;

    // Adaptive threshold knobs -- exposed so surface-specific tuning doesn't
    // require a rebuild. blockSize must be odd and >= 3; C is "how much
    // darker than the local mean a pixel has to be to count as foreground".
    // Textured surfaces (cast magnetic tile, sandblasted metal, etc.) usually
    // need a larger blockSize and a larger C than smooth painted surfaces.
    int adaptiveBlockSize = 51;
    double adaptiveC = 10.0;
};

}  // namespace mvi
