"""
Advisory Photo-Diff Service using Pillow.
Compares before-condition and after-condition photos of lab equipment,
highlights changed regions with a translucent warning mask, and stamps
the resulting visual diff with:
"ADVISORY ONLY — A HUMAN DECIDES".
Flags potential anomalies for manager/owner review without automated penalties.
"""
from __future__ import annotations

import os
import uuid
from typing import Any, Dict, Optional
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from app.services.storage_service import PRIVATE_STORAGE_DIR, get_photo_path

SIGNIFICANT_DIFF_THRESHOLD_PCT = 5.0  # 5% visual change triggers owner advisory flag


def compare_condition_photos(
    pre_filename: str,
    post_filename: str,
) -> Dict[str, Any]:
    """
    Compares two condition photos (PRE vs POST session).
    Generates a highlighted diff image saved privately, calculates the altered area percentage,
    and returns advisory metadata.
    """
    pre_path = get_photo_path(pre_filename)
    post_path = get_photo_path(post_filename)

    if not pre_path or not post_path:
        return {
            "change_percentage": 0.0,
            "is_significant": False,
            "diff_photo_filename": None,
            "advisory_label": "Advisory only — a human decides",
            "flagged_for_owner": False,
            "summary": "Comparison skipped: one or both condition photos unavailable.",
        }

    try:
        # Standardize size for robust pixel-to-pixel comparison
        target_size = (640, 480)
        img_pre = Image.open(pre_path).convert("RGB").resize(target_size, Image.Resampling.LANCZOS)
        img_post = Image.open(post_path).convert("RGB").resize(target_size, Image.Resampling.LANCZOS)

        # 1. Absolute pixel difference in RGB
        diff_rgb = ImageChops.difference(img_pre, img_post)
        diff_gray = diff_rgb.convert("L")

        # 2. Smooth minor sensor/lighting noise
        diff_blurred = diff_gray.filter(ImageFilter.BoxBlur(2))

        # 3. Threshold mask: differences above 28 intensity units are flagged
        threshold = 28
        mask = diff_blurred.point(lambda p: 255 if p > threshold else 0, mode="1")

        # Calculate percentage of changed pixels
        total_pixels = target_size[0] * target_size[1]
        # In mode '1', 255 is True/white
        get_pixels = getattr(mask, "get_flattened_data", mask.getdata)
        changed_pixels = sum(1 for p in get_pixels() if p == 255)
        change_pct = round((changed_pixels / float(total_pixels)) * 100.0, 2)

        is_significant = change_pct >= SIGNIFICANT_DIFF_THRESHOLD_PCT

        # 4. Create visual diff overlay
        # Start with the POST image
        diff_canvas = img_post.copy().convert("RGBA")
        overlay = Image.new("RGBA", target_size, (0, 0, 0, 0))
        draw_overlay = ImageDraw.Draw(overlay)

        # Draw red translucent pixels over changed coordinates
        mask_data = mask.load()
        w, h = target_size
        for x in range(w):
            for y in range(h):
                if mask_data[x, y] == 255:
                    overlay.putpixel((x, y), (255, 38, 38, 140))  # Semi-transparent red highlight

        # Highlight bounding boxes of significant changes
        bbox = mask.getbbox()
        if bbox:
            # Draw a bounding warning rectangle around the affected region
            draw_overlay.rectangle(bbox, outline=(255, 215, 0, 230), width=3)

        # Composite the overlay onto the POST image
        diff_canvas = Image.alpha_composite(diff_canvas, overlay).convert("RGB")

        # 5. Stamp mandatory advisory banner on the diff image
        draw = ImageDraw.Draw(diff_canvas)
        # Top banner bar
        banner_height = 42
        draw.rectangle([0, 0, w, banner_height], fill=(18, 24, 38))
        draw.line([0, banner_height, w, banner_height], fill=(239, 68, 68), width=2)

        banner_text = f"[ADVISORY ONLY — A HUMAN DECIDES] Visual Change: {change_pct}%"
        sub_text = "AI inspection flags potential alteration for owner review; penalties require manager confirmation."
        
        # Draw banner text with default basic font
        draw.text((12, 6), banner_text, fill=(255, 255, 255))
        draw.text((12, 24), sub_text, fill=(203, 213, 225))

        # Bottom watermark
        draw.rectangle([0, h - 22, w, h], fill=(18, 24, 38))
        draw.text((12, h - 18), "OpenBench Advisory Photo-Diff Engine • Pillow", fill=(148, 163, 184))

        # 6. Save diff image to private storage
        diff_filename = f"diff_{uuid.uuid4().hex[:14]}.jpg"
        diff_dest = PRIVATE_STORAGE_DIR / diff_filename
        diff_canvas.save(diff_dest, "JPEG", quality=88)

        summary = (
            f"Advisory visual diff detected {change_pct}% altered surface area. Flagged for owner review."
            if is_significant
            else f"Normal visual consistency maintained ({change_pct}% minor optical variance detected)."
        )

        return {
            "change_percentage": change_pct,
            "is_significant": is_significant,
            "diff_photo_filename": diff_filename,
            "advisory_label": "Advisory only — a human decides",
            "flagged_for_owner": is_significant,
            "summary": summary,
        }

    except Exception as exc:
        return {
            "change_percentage": 0.0,
            "is_significant": False,
            "diff_photo_filename": None,
            "advisory_label": "Advisory only — a human decides",
            "flagged_for_owner": False,
            "summary": f"Visual diff evaluation encountered an error: {str(exc)}",
        }
