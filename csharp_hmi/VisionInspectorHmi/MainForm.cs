using System;
using System.Drawing;
using System.IO;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace VisionInspectorHmi;

/// <summary>
/// Minimal HMI emulating an operator panel: image picker, knobs for the same
/// thresholds the C++ CLI accepts, run button, and a verdict banner.
///
/// This is intentionally small. The whole point is that the inspection logic
/// is C++ and the HMI is a thin wrapper.
/// </summary>
public sealed class MainForm : Form
{
    private readonly TextBox _imagePathBox = new() { Width = 380, ReadOnly = true };
    private readonly Button _browseButton = new() { Text = "이미지 선택", Width = 100 };
    private readonly NumericUpDown _pixelToMm = new()
    {
        DecimalPlaces = 4, Increment = 0.005m, Minimum = 0.0001m,
        Maximum = 10m, Value = 0.05m, Width = 90,
    };
    private readonly NumericUpDown _maxDefectCount = new()
    {
        Minimum = 0, Maximum = 999, Value = 3, Width = 90,
    };
    private readonly NumericUpDown _maxAreaMm2 = new()
    {
        DecimalPlaces = 2, Increment = 0.1m, Minimum = 0m, Maximum = 10_000m,
        Value = 2.0m, Width = 90,
    };
    private readonly NumericUpDown _maxLengthMm = new()
    {
        DecimalPlaces = 2, Increment = 0.1m, Minimum = 0m, Maximum = 10_000m,
        Value = 5.0m, Width = 90,
    };
    private readonly NumericUpDown _minAreaPx = new()
    {
        Minimum = 1, Maximum = 100_000, Value = 30, Width = 90,
    };

    private readonly Button _runButton = new() { Text = "검사 시작", Width = 120, Height = 36 };
    private readonly Label _verdictLabel = new()
    {
        Text = "READY", Font = new Font(SystemFonts.DefaultFont.FontFamily, 24, FontStyle.Bold),
        AutoSize = true,
    };
    private readonly Label _metricsLabel = new() { AutoSize = true };
    private readonly PictureBox _originalImage = new()
    {
        SizeMode = PictureBoxSizeMode.Zoom, BorderStyle = BorderStyle.FixedSingle,
        Width = 360, Height = 360,
    };
    private readonly PictureBox _resultImage = new()
    {
        SizeMode = PictureBoxSizeMode.Zoom, BorderStyle = BorderStyle.FixedSingle,
        Width = 360, Height = 360,
    };
    private readonly TextBox _logBox = new()
    {
        Multiline = true, ScrollBars = ScrollBars.Vertical, ReadOnly = true,
        Width = 760, Height = 140,
    };

    private readonly InspectorRunner _runner = new();

    public MainForm()
    {
        Text = "Vision Inspector HMI";
        ClientSize = new Size(820, 720);
        StartPosition = FormStartPosition.CenterScreen;

        _browseButton.Click += (_, _) => BrowseImage();
        _runButton.Click += async (_, _) => await RunInspectionAsync();

        BuildLayout();
    }

    private void BuildLayout()
    {
        var top = new FlowLayoutPanel
        {
            FlowDirection = FlowDirection.LeftToRight,
            AutoSize = true, Padding = new Padding(8),
        };
        top.Controls.Add(_imagePathBox);
        top.Controls.Add(_browseButton);

        var knobs = new TableLayoutPanel
        {
            ColumnCount = 4, RowCount = 3, AutoSize = true, Padding = new Padding(8),
        };
        knobs.Controls.Add(new Label { Text = "pixel_to_mm", AutoSize = true }, 0, 0);
        knobs.Controls.Add(_pixelToMm, 1, 0);
        knobs.Controls.Add(new Label { Text = "max_defect_count", AutoSize = true }, 2, 0);
        knobs.Controls.Add(_maxDefectCount, 3, 0);
        knobs.Controls.Add(new Label { Text = "max_area_mm²", AutoSize = true }, 0, 1);
        knobs.Controls.Add(_maxAreaMm2, 1, 1);
        knobs.Controls.Add(new Label { Text = "max_length_mm", AutoSize = true }, 2, 1);
        knobs.Controls.Add(_maxLengthMm, 3, 1);
        knobs.Controls.Add(new Label { Text = "min_contour_area_px", AutoSize = true }, 0, 2);
        knobs.Controls.Add(_minAreaPx, 1, 2);
        knobs.Controls.Add(_runButton, 3, 2);

        var images = new FlowLayoutPanel
        {
            FlowDirection = FlowDirection.LeftToRight,
            AutoSize = true, Padding = new Padding(8),
        };
        images.Controls.Add(WrapPictureBox(_originalImage, "원본"));
        images.Controls.Add(WrapPictureBox(_resultImage, "결과"));

        var bottom = new FlowLayoutPanel
        {
            FlowDirection = FlowDirection.TopDown,
            AutoSize = true, Padding = new Padding(8),
        };
        bottom.Controls.Add(_verdictLabel);
        bottom.Controls.Add(_metricsLabel);
        bottom.Controls.Add(_logBox);

        var root = new FlowLayoutPanel
        {
            FlowDirection = FlowDirection.TopDown, Dock = DockStyle.Fill,
        };
        root.Controls.Add(top);
        root.Controls.Add(knobs);
        root.Controls.Add(images);
        root.Controls.Add(bottom);
        Controls.Add(root);
    }

    private static Control WrapPictureBox(PictureBox box, string caption)
    {
        var p = new FlowLayoutPanel
        {
            FlowDirection = FlowDirection.TopDown, AutoSize = true,
            Padding = new Padding(4),
        };
        p.Controls.Add(new Label { Text = caption, AutoSize = true });
        p.Controls.Add(box);
        return p;
    }

    private void BrowseImage()
    {
        using var dlg = new OpenFileDialog
        {
            Title = "검사 이미지 선택",
            Filter = "Images|*.png;*.jpg;*.jpeg;*.bmp|All files|*.*",
        };
        if (dlg.ShowDialog(this) == DialogResult.OK)
        {
            _imagePathBox.Text = dlg.FileName;
            try
            {
                using var fs = File.OpenRead(dlg.FileName);
                _originalImage.Image?.Dispose();
                _originalImage.Image = Image.FromStream(fs);
            }
            catch (Exception ex)
            {
                Log($"원본 이미지를 표시할 수 없습니다: {ex.Message}");
            }
        }
    }

    private async Task RunInspectionAsync()
    {
        if (string.IsNullOrWhiteSpace(_imagePathBox.Text))
        {
            MessageBox.Show(this, "먼저 이미지를 선택해 주세요.");
            return;
        }

        _runner.Config = new InspectorConfig
        {
            PixelToMm = (double)_pixelToMm.Value,
            MaxDefectCount = (int)_maxDefectCount.Value,
            MaxDefectAreaMm2 = (double)_maxAreaMm2.Value,
            MaxDefectLengthMm = (double)_maxLengthMm.Value,
            MinContourAreaPx = (int)_minAreaPx.Value,
        };

        _runButton.Enabled = false;
        _verdictLabel.Text = "RUNNING...";
        _verdictLabel.ForeColor = Color.DimGray;
        try
        {
            var run = await _runner.RunAsync(_imagePathBox.Text);
            ApplyResult(run);
        }
        catch (Exception ex)
        {
            _verdictLabel.Text = "ERROR";
            _verdictLabel.ForeColor = Color.Red;
            Log(ex.Message);
        }
        finally
        {
            _runButton.Enabled = true;
        }
    }

    private void ApplyResult(InspectionRun run)
    {
        var report = run.Report;
        if (run.ResultImagePath is not null && File.Exists(run.ResultImagePath))
        {
            using var fs = File.OpenRead(run.ResultImagePath);
            _resultImage.Image?.Dispose();
            _resultImage.Image = Image.FromStream(fs);
        }

        if (report is null)
        {
            _verdictLabel.Text = "NO REPORT";
            _verdictLabel.ForeColor = Color.OrangeRed;
            Log($"보고서를 찾을 수 없습니다. stdout: {run.Stdout}");
            return;
        }

        _verdictLabel.Text = report.Result ?? "UNKNOWN";
        _verdictLabel.ForeColor = report.Result switch
        {
            "OK" => Color.SeaGreen,
            "NG" => Color.Crimson,
            _ => Color.OrangeRed,
        };
        _metricsLabel.Text =
            $"defects = {report.DefectCount}    " +
            $"max_area = {report.MaxAreaMm2:F4} mm²    " +
            $"max_length = {report.MaxLengthMm:F4} mm    " +
            $"total_area = {report.TotalAreaMm2:F4} mm²    " +
            $"elapsed = {run.ElapsedMs:F1} ms";
        Log($"binary={run.Binary}");
        Log($"args={run.Args}");
        Log($"report={run.JsonReportPath}");
        Log(run.Stdout);
    }

    private void Log(string line)
    {
        if (string.IsNullOrWhiteSpace(line)) return;
        _logBox.AppendText(line.TrimEnd() + Environment.NewLine);
    }
}
