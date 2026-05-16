using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;

namespace VisionInspectorHmi;

/// <summary>
/// Thin wrapper around the C++ vision_inspector binary.
/// Mirrors scripts/run_cpp_inspector.py so the HMI behaves identically to the
/// Streamlit UI.
/// </summary>
public sealed class InspectorRunner
{
    public InspectorConfig Config { get; set; } = new();
    public string OutputDir { get; set; } = Path.Combine("data", "results");
    public string? ExplicitBinaryPath { get; set; }

    private static readonly string[] CandidateRelativePaths =
    {
        "build/vision_inspector.exe",
        "build/Release/vision_inspector.exe",
        "build/Debug/vision_inspector.exe",
        "build/vision_inspector",
        "cpp/build/vision_inspector.exe",
        "cpp/build/Release/vision_inspector.exe",
        "cpp/build/Debug/vision_inspector.exe",
        "cpp/build/vision_inspector",
    };

    public string? FindBinary(string? repoRoot = null)
    {
        if (!string.IsNullOrEmpty(ExplicitBinaryPath) && File.Exists(ExplicitBinaryPath))
        {
            return ExplicitBinaryPath;
        }

        repoRoot ??= Environment.CurrentDirectory;
        foreach (var rel in CandidateRelativePaths)
        {
            var full = Path.Combine(repoRoot, rel);
            if (File.Exists(full))
            {
                return full;
            }
        }

        // Fallback: walk up a few levels in case the exe is launched from
        // bin/Debug/... rather than the repo root.
        var dir = new DirectoryInfo(repoRoot);
        for (int i = 0; i < 5 && dir != null; ++i)
        {
            foreach (var rel in CandidateRelativePaths)
            {
                var full = Path.Combine(dir.FullName, rel);
                if (File.Exists(full))
                {
                    return full;
                }
            }
            dir = dir.Parent;
        }

        return null;
    }

    public async Task<InspectionRun> RunAsync(string imagePath, string? repoRoot = null)
    {
        var binary = FindBinary(repoRoot);
        if (binary is null)
        {
            throw new FileNotFoundException(
                "vision_inspector binary not found. Build it first:\n" +
                "  cmake -S cpp -B build && cmake --build build");
        }

        Directory.CreateDirectory(OutputDir);
        var args = new List<string>
        {
            "--image", imagePath,
            "--output", OutputDir,
            "--pixel-to-mm", Config.PixelToMm.ToString("R"),
            "--max-defect-count", Config.MaxDefectCount.ToString(),
            "--max-defect-area-mm2", Config.MaxDefectAreaMm2.ToString("R"),
            "--max-defect-length-mm", Config.MaxDefectLengthMm.ToString("R"),
            "--min-contour-area-px", Config.MinContourAreaPx.ToString(),
        };

        var psi = new ProcessStartInfo
        {
            FileName = binary,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        foreach (var a in args) psi.ArgumentList.Add(a);

        using var proc = new Process { StartInfo = psi };
        var sw = Stopwatch.StartNew();
        proc.Start();
        var stdoutTask = proc.StandardOutput.ReadToEndAsync();
        var stderrTask = proc.StandardError.ReadToEndAsync();
        await proc.WaitForExitAsync();
        sw.Stop();

        var stdout = await stdoutTask;
        var stderr = await stderrTask;
        if (proc.ExitCode != 0)
        {
            throw new InvalidOperationException(
                $"vision_inspector exited with {proc.ExitCode}\nstderr: {stderr}");
        }

        var baseName = Path.GetFileNameWithoutExtension(imagePath);
        var jsonPath = Path.Combine(OutputDir, $"inspection_report_{baseName}.json");
        var resultImage = Path.Combine(OutputDir, $"result_{baseName}.png");

        InspectionReport? report = null;
        if (File.Exists(jsonPath))
        {
            using var fs = File.OpenRead(jsonPath);
            report = await JsonSerializer.DeserializeAsync<InspectionReport>(
                fs, new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true,
                });
        }

        return new InspectionRun
        {
            Binary = binary,
            Args = string.Join(' ', args),
            Stdout = stdout,
            Stderr = stderr,
            ElapsedMs = sw.Elapsed.TotalMilliseconds,
            JsonReportPath = File.Exists(jsonPath) ? jsonPath : null,
            ResultImagePath = File.Exists(resultImage) ? resultImage : null,
            Report = report,
        };
    }
}

public sealed class InspectorConfig
{
    public double PixelToMm { get; set; } = 0.05;
    public int MaxDefectCount { get; set; } = 3;
    public double MaxDefectAreaMm2 { get; set; } = 2.0;
    public double MaxDefectLengthMm { get; set; } = 5.0;
    public int MinContourAreaPx { get; set; } = 30;
}

public sealed class InspectionRun
{
    public string Binary { get; init; } = "";
    public string Args { get; init; } = "";
    public string Stdout { get; init; } = "";
    public string Stderr { get; init; } = "";
    public double ElapsedMs { get; init; }
    public string? JsonReportPath { get; init; }
    public string? ResultImagePath { get; init; }
    public InspectionReport? Report { get; init; }
}
