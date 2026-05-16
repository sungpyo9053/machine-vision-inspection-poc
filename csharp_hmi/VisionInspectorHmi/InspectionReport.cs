using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace VisionInspectorHmi;

/// <summary>
/// 1:1 mirror of the JSON produced by ReportWriter::saveJsonReport in C++.
/// </summary>
public sealed class InspectionReport
{
    [JsonPropertyName("image_name")]
    public string? ImageName { get; set; }

    [JsonPropertyName("result")]
    public string? Result { get; set; }

    [JsonPropertyName("defect_count")]
    public int DefectCount { get; set; }

    [JsonPropertyName("max_area_mm2")]
    public double MaxAreaMm2 { get; set; }

    [JsonPropertyName("max_length_mm")]
    public double MaxLengthMm { get; set; }

    [JsonPropertyName("total_area_mm2")]
    public double TotalAreaMm2 { get; set; }

    [JsonPropertyName("created_at")]
    public string? CreatedAt { get; set; }

    [JsonPropertyName("defects")]
    public List<DefectInfo> Defects { get; set; } = new();
}

public sealed class DefectInfo
{
    [JsonPropertyName("defect_id")]
    public int DefectId { get; set; }

    [JsonPropertyName("bbox")]
    public Bbox Bbox { get; set; } = new();

    [JsonPropertyName("center")]
    public Center Center { get; set; } = new();

    [JsonPropertyName("area_px")]
    public double AreaPx { get; set; }

    [JsonPropertyName("area_mm2")]
    public double AreaMm2 { get; set; }

    [JsonPropertyName("length_px")]
    public double LengthPx { get; set; }

    [JsonPropertyName("length_mm")]
    public double LengthMm { get; set; }
}

public sealed class Bbox
{
    public int X { get; set; }
    public int Y { get; set; }
    public int W { get; set; }
    public int H { get; set; }
}

public sealed class Center
{
    public double X { get; set; }
    public double Y { get; set; }
}
