"""Image processing utilities.

CONTRACT
- Inputs: Image paths, parameters
- Outputs: Processed images, analysis reports
- Invariants:
  - remove-magenta: produces transparent PNGs from magenta backgrounds
  - analyze: validates transparency and foreground integrity
  - resize: resizes preserving aspect ratio
- Failure:
  - Raises typer.Exit(1) on IO errors or validation failures
"""

import math
from pathlib import Path
from typing import Annotated

try:
    import typer
    from PIL import Image
except ImportError as e:
    raise ImportError(f"Missing dependency: {e}. Please install 'typer' and 'pillow'.") from e


app = typer.Typer(help="Image processing utilities.")


def _is_magenta(r: int, g: int, b: int, threshold: int) -> bool:
    # Magenta is high R, high B, low G.
    # Distance from (255, 0, 255)
    dist = math.sqrt((r - 255) ** 2 + (g - 0) ** 2 + (b - 255) ** 2)
    return dist < threshold


@app.command()
def remove_magenta(
    img_path: Annotated[Path, typer.Option("--in", exists=True, help="Input image path")],
    out_path: Annotated[Path, typer.Option("--out", help="Output image path")],
    bg_color: str = "#ff00ff",
    threshold: int = 200,
    choke_px: int = 2,
):
    """Remove magenta background using pure alpha masking.
    
    CORRECT APPROACH:
    1. Never modify RGB of any pixel
    2. Create binary alpha mask based on magenta detection
    3. Apply inward erosion (choke) to remove fringe
    4. No blur - erosion provides clean edges
    
    Args:
        threshold: Color distance from pure magenta (lower = stricter)
        choke_px: Pixels to erode inward (removes contaminated edge)
    """
    try:
        from PIL import ImageFilter
        img = Image.open(img_path).convert("RGBA")
    except Exception as e:
        typer.echo(f"Error opening image: {e}", err=True)
        raise typer.Exit(1) from e

    width, height = img.size
    pixels = img.load()
    
    # Parse background color
    bg_r, bg_g, bg_b = 255, 0, 255
    if bg_color.startswith("#") and len(bg_color) == 7:
        bg_r = int(bg_color[1:3], 16)
        bg_g = int(bg_color[3:5], 16)
        bg_b = int(bg_color[5:7], 16)
    
    # Helper: Detect pure magenta (not purple anvil colors)
    def is_magenta(r, g, b, thresh):
        # Distance check
        dist = math.sqrt((r - bg_r) ** 2 + (g - bg_g) ** 2 + (b - bg_b) ** 2)
        if dist > thresh:
            return False
        
        # Green ratio check: magenta has low green relative to red+blue
        # Adjusted to 0.35 to catch Gemini logo and edge pixels
        if r + b > 100:
            green_ratio = g / (r + b)
            if green_ratio > 0.35:  # Relaxed to catch more magenta
                return False
        
        return True
    
    # Create binary alpha mask (255 = keep, 0 = remove)
    mask = Image.new("L", (width, height), 0)
    mask_pixels = mask.load()
    
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            # If NOT magenta, keep it
            if not is_magenta(r, g, b, threshold):
                mask_pixels[x, y] = 255
    
    # Apply inward erosion (choke) to remove contaminated edge
    # This shrinks the foreground slightly, removing fringe
    if choke_px > 0:
        # MinFilter erodes (shrinks white areas)
        kernel_size = (choke_px * 2) + 1
        mask = mask.filter(ImageFilter.MinFilter(kernel_size))
    
    # Apply mask - NEVER modified any RGB values!
    img.putalpha(mask)
    img.save(out_path)
    typer.echo(f"Saved to {out_path} (threshold={threshold}, choke={choke_px}px)")


@app.command()
def analyze(
    original_path: Annotated[Path, typer.Option("--original", exists=True)],
    cutout_path: Annotated[Path, typer.Option("--cutout", exists=True)],
    alpha_min: int = 16,
    magenta_threshold: int = 50,
):
    """Analyze cutout quality."""
    orig = Image.open(original_path).convert("RGBA")
    cut = Image.open(cutout_path).convert("RGBA")

    if orig.size != cut.size:
        typer.echo("Sizes differ!", err=True)
        raise typer.Exit(1)

    width, height = orig.size
    total_pixels = width * height
    spill_count = 0

    diff_sum = 0
    diff_max = 0
    opaque_count = 0

    o_pix = orig.load()
    c_pix = cut.load()

    for y in range(height):
        for x in range(width):
            or_, og, ob, oa = o_pix[x, y]
            cr, cg, cb, ca = c_pix[x, y]

            # Check spill: meaningful alpha AND still looks magenta?
            if ca >= alpha_min:
                dist = math.sqrt((cr - 255) ** 2 + (cg - 0) ** 2 + (cb - 255) ** 2)
                if dist < magenta_threshold:
                    spill_count += 1

            # Check integrity: if opaque in result, should match original (ignoring background)
            if ca >= 250:
                # We assume original had the object there.
                # If original was magenta background, we shouldn't be opaque there.
                # Use original pixel to check if it was foreground?
                # User contract: "opaque foreground pixels are not significantly changed"

                # If original was NOT magenta (foreground), difference should be low.
                # If original WAS magenta, result should be transparent (handled in spill check).

                # Let's just compare RGB distance for opaque output pixels.
                d_pix = math.sqrt((or_ - cr) ** 2 + (og - cg) ** 2 + (ob - cb) ** 2)
                diff_sum += d_pix
                diff_max = max(diff_max, d_pix)
                opaque_count += 1

    spill_pct = (spill_count / total_pixels) * 100
    mean_diff = (diff_sum / opaque_count) if opaque_count > 0 else 0.0

    print(f"Total pixels: {total_pixels}")
    print(
        f"Spill (alpha>={alpha_min}, magenta-dist<{magenta_threshold}): "
        f"{spill_count} ({spill_pct:.4f}%)"
    )
    print(f"Integrity (alpha>=250): mean_diff={mean_diff:.4f}, max_diff={diff_max:.4f}")

    if spill_pct > 0.1:  # Default tiny tolerance
        typer.echo("FAIL: Too much spill.", err=True)
        raise typer.Exit(1)

    print("PASS")


@app.command()
def resize(
    img_path: Annotated[Path, typer.Option("--in", exists=True)],
    out_path: Annotated[Path, typer.Option("--out")],
    max_width: int = 800,
    max_height: int = 800,
    format: str = "png",
    quality: int = 85,
    optimize: bool = False,
):
    """Resize an image."""
    img = Image.open(img_path)
    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    
    kwargs = {}
    if format.lower() in ("jpg", "jpeg"):
        img = img.convert("RGB")
        kwargs["quality"] = quality
    elif format.lower() == "webp":
        kwargs["quality"] = quality
    
    if optimize:
        kwargs["optimize"] = True

    img.save(out_path, format=format, **kwargs)
    typer.echo(f"Resized to {out_path} ({img.size})")


if __name__ == "__main__":
    app()
