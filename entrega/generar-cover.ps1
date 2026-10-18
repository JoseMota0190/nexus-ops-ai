Add-Type -AssemblyName System.Drawing

$W = 1200; $H = 630
$bmp = New-Object System.Drawing.Bitmap($W, $H)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit

# --- Fondo con degradé azul noche ---
$rect = New-Object System.Drawing.Rectangle(0, 0, $W, $H)
$bg = New-Object System.Drawing.Drawing2D.LinearGradientBrush($rect,
    [System.Drawing.Color]::FromArgb(255, 6, 11, 31),
    [System.Drawing.Color]::FromArgb(255, 14, 26, 68), 115.0)
$g.FillRectangle($bg, $rect)

# --- Manchas de color (azul/violeta) ---
function Blob([int]$cx, [int]$cy, [int]$r, [int]$a, [int]$rr, [int]$gg, [int]$bb) {
    $p = New-Object System.Drawing.Drawing2D.GraphicsPath
    $p.AddEllipse($cx - $r, $cy - $r, 2 * $r, 2 * $r)
    $pgb = New-Object System.Drawing.Drawing2D.PathGradientBrush($p)
    $pgb.CenterColor = [System.Drawing.Color]::FromArgb($a, $rr, $gg, $bb)
    $pgb.SurroundColors = @([System.Drawing.Color]::FromArgb(0, $rr, $gg, $bb))
    $g.FillPath($pgb, $p)
    $p.Dispose(); $pgb.Dispose()
}
Blob 1080 -40 420 150 122 90 248
Blob 120 700 380 110 34 211 238

# --- Chevron (logo) en degradé violeta->azul ---
$chev = New-Object System.Drawing.Drawing2D.GraphicsPath
$pts = @(
    (New-Object System.Drawing.PointF(96, 88)),
    (New-Object System.Drawing.PointF(150, 188)),
    (New-Object System.Drawing.PointF(128, 188)),
    (New-Object System.Drawing.PointF(96, 122)),
    (New-Object System.Drawing.PointF(64, 188)),
    (New-Object System.Drawing.PointF(42, 188))
)
$chev.AddPolygon($pts)
$chevBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
    (New-Object System.Drawing.PointF(42, 88)), (New-Object System.Drawing.PointF(150, 188)),
    [System.Drawing.Color]::FromArgb(255, 122, 90, 248),
    [System.Drawing.Color]::FromArgb(255, 47, 107, 255))
$g.FillPath($chevBrush, $chev)

# --- Tipografías ---
$fMarca  = New-Object System.Drawing.Font("Segoe UI", 20, [System.Drawing.FontStyle]::Bold)
$fTitulo = New-Object System.Drawing.Font("Segoe UI", 68, [System.Drawing.FontStyle]::Bold)
$fSub    = New-Object System.Drawing.Font("Segoe UI", 28, [System.Drawing.FontStyle]::Regular)
$fLinea  = New-Object System.Drawing.Font("Segoe UI", 22, [System.Drawing.FontStyle]::Regular)
$fTag    = New-Object System.Drawing.Font("Segoe UI", 18, [System.Drawing.FontStyle]::Bold)

$blanco = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 234, 240, 251))
$suave  = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 159, 176, 208))
$cyan   = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 34, 211, 238))
$rojo   = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 255, 92, 122))

# Marca
$g.DrawString("NEXUS  ALARM", $fMarca, $blanco, 168, 118)

# Título
$g.DrawString("nexus-ops-ai", $fTitulo, $blanco, 92, 240)

# Bajada
$g.DrawString("The digital twin of Nexus Alarm", $fSub, $suave, 96, 340)

# Línea descriptiva
$g.DrawString("A swarm of AI agents running a small company's full sales operation.", $fLinea, $blanco, 96, 392)
$g.DrawString("Calls  |  scheduling  |  dispatch  |  monthly management  |  Monte Carlo.", $fLinea, $cyan, 96, 424)

# Chip AMD
$chip = New-Object System.Drawing.RectangleF(96, 500, 92, 40)
$g.FillRectangle((New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 255, 92, 122))), $chip)
$g.DrawString("AMD", $fTag, (New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)), 116, 508)
$g.DrawString("AMD Developer Hackathon ACT III  |  Reinvent Commerce", $fTag, $blanco, 208, 508)

$bmp.Save("$PSScriptRoot\cover.png", [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Output "cover.png generado ($W x $H)"
