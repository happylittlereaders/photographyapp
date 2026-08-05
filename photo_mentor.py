"""
photo_mentor.py
----------------
Core analysis, composition guides (Golden Spiral, Golden Triangles, etc.),
and image correction logic with two-way auto-fixing for exposure and saturation,
plus photographer style transfer capability.
"""

import cv2
import numpy as np


class PhotoMentor:
    """Runs computer-vision checks and applies automatic fixes to photos."""

    def __init__(self, image_path: str):
        self.image_path = image_path
        self.img = cv2.imread(image_path)
        if self.img is None:
            raise FileNotFoundError(
                f"Could not read image at '{image_path}'. "
                "Check the path and make sure it's a valid image file."
            )

        self.gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        self.hsv = cv2.cvtColor(self.img, cv2.COLOR_BGR2HSV)
        self.height, self.width = self.gray.shape

    # -----------------------------------------------------------------
    # Metric Analysis Methods
    # -----------------------------------------------------------------
    def analyze_exposure(self):
        avg_brightness = float(np.mean(self.gray))
        overexposed_ratio = float(np.sum(self.gray > 240)) / self.gray.size

        if overexposed_ratio > 0.10 or avg_brightness > 170:
            grade = "Overexposed"
            advice = "Highlights are clipped or too bright. Lowering exposure restores highlight detail."
        elif avg_brightness < 60:
            grade = "Underexposed"
            advice = "The image is quite dark. Brightening shadows and midtones uncovers hidden details."
        elif 100 <= avg_brightness <= 160:
            grade = "Well exposed"
            advice = "Brightness is well balanced, with good detail in both shadows and highlights."
        else:
            grade = "Acceptable exposure"
            advice = "Exposure is reasonable, but subtle tone mapping can balance it further."

        return grade, advice, avg_brightness

    def fix_exposure(self, img_bgr=None):
        src = self.img if img_bgr is None else img_bgr
        gray_src = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
        avg_brightness = float(np.mean(gray_src))
        overexposed_ratio = float(np.sum(gray_src > 240)) / gray_src.size

        target_brightness = 110.0 if overexposed_ratio > 0.10 else 128.0
        if avg_brightness < 1.0:
            avg_brightness = 1.0

        gamma = np.clip(target_brightness / avg_brightness, 0.80, 1.25)
        inv_gamma = 1.0 / gamma
        table = np.array(
            [((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]
        ).astype("uint8")

        adjusted = cv2.LUT(src, table)
        return cv2.addWeighted(src, 0.60, adjusted, 0.40, 0)

    def analyze_composition(self):
        edges = cv2.Canny(self.gray, 50, 150)
        min_length = max(1, min(self.width, self.height) // 4)

        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=100,
            minLineLength=min_length, maxLineGap=10
        )

        max_tilt = 0.0
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line.ravel()
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                if 1 < abs(angle) < 20 and abs(angle) > abs(max_tilt):
                    max_tilt = angle

        if abs(max_tilt) > 2:
            direction = "clockwise" if max_tilt > 0 else "counter-clockwise"
            grade = "Tilted"
            advice = f"The horizon appears tilted about {abs(max_tilt):.1f}° {direction}. Auto-rotating to level it."
        else:
            grade = "Level"
            advice = "No significant tilt detected — the horizon looks level."

        return grade, advice, max_tilt

    def fix_composition(self, img_bgr=None):
        src = self.img if img_bgr is None else img_bgr
        _, _, tilt = self.analyze_composition()

        if abs(tilt) <= 2:
            return src.copy()

        center = (self.width // 2, self.height // 2)
        matrix = cv2.getRotationMatrix2D(center, tilt, 1.0)
        return cv2.warpAffine(
            src, matrix, (self.width, self.height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )

    def analyze_sharpness(self):
        sharpness = cv2.Laplacian(self.gray, cv2.CV_64F).var()

        if sharpness < 40:
            grade = "Possibly blurry"
            advice = "Detail looks soft. Applying subtle unsharp masking will enhance key edges."
        elif sharpness < 250:
            grade = "Acceptably sharp"
            advice = "Sharpness is reasonable for most uses."
        else:
            grade = "Very sharp"
            advice = "Excellent detail retention."

        return grade, advice, sharpness

    def fix_sharpness(self, img_bgr=None):
        src = self.img if img_bgr is None else img_bgr
        grade, _, _ = self.analyze_sharpness()

        if grade != "Possibly blurry":
            return src.copy()

        blurred = cv2.GaussianBlur(src, (0, 0), 2.0)
        return cv2.addWeighted(src, 1.15, blurred, -0.15, 0)

    def analyze_saturation(self):
        avg_saturation = float(np.mean(self.hsv[:, :, 1]))

        if avg_saturation < 30:
            grade = "Washed out"
            advice = "Colors look pale. Boosting saturation will make the photo feel more vivid."
        elif avg_saturation > 180:
            grade = "Oversaturated"
            advice = "Colors are very intense. Desaturating slightly produces a more natural look."
        else:
            grade = "Natural"
            advice = "Color intensity looks natural and well balanced."

        return grade, advice, avg_saturation

    def fix_saturation(self, img_bgr=None):
        src = self.img if img_bgr is None else img_bgr
        hsv = cv2.cvtColor(src, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        avg_sat = np.mean(s)
        if avg_sat < 30:
            s = cv2.add(s, 25)
        elif avg_sat > 180:
            s = cv2.subtract(s, 30)

        fixed_hsv = cv2.merge((h, s, v))
        return cv2.cvtColor(fixed_hsv, cv2.COLOR_HSV2BGR)

    def generate_master_fixed_image(self):
        fixed = self.fix_exposure(self.img)
        fixed = self.fix_composition(fixed)
        fixed = self.fix_sharpness(fixed)
        fixed = self.fix_saturation(fixed)
        return fixed

    # -----------------------------------------------------------------
    # Photographer Style Transfer Engine
    # -----------------------------------------------------------------
    def apply_photographer_style(self, base_image, style_config):
        """
        Applies aesthetic styling (contrast, color grading, monochrome, grain, vignette)
        matching selected photographer presets.
        """
        img = base_image.copy().astype(np.float32)
        
        contrast = style_config.get("contrast_factor", 1.0)
        sat_mult = style_config.get("saturation_factor", 1.0)
        monochrome = style_config.get("monochrome", False)
        grain = style_config.get("grain", False)
        vignette = style_config.get("vignette", False)
        warmth = style_config.get("warmth", 0.0)
        cool_shadows = style_config.get("cool_shadows", False)

        # 1. Apply Contrast & Warmth / Shadow Tints
        img = (img - 127.5) * contrast + 127.5
        if warmth != 0.0:
            img[:, :, 2] += warmth * 15  # Red channel boost
            img[:, :, 0] -= warmth * 10  # Blue channel pull
        
        if cool_shadows:
            shadow_mask = np.clip((128.0 - img) / 128.0, 0, 1)
            img[:, :, 0] += shadow_mask[:, :, 0] * 18.0  # Blue boost in shadows

        img = np.clip(img, 0, 255).astype(np.uint8)

        # 2. Saturation & Monochrome Adjustment
        if monochrome:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        elif sat_mult != 1.0:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * sat_mult, 0, 255)
            img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # 3. Add Film Grain
        if grain:
            noise = np.random.normal(0, 12, img.shape).astype(np.float32)
            img = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        # 4. Apply Vignette Effect
        if vignette:
            rows, cols = img.shape[:2]
            kernel_x = cv2.getGaussianKernel(cols, cols * 0.5)
            kernel_y = cv2.getGaussianKernel(rows, rows * 0.5)
            kernel = kernel_y * kernel_x.T
            mask = kernel / kernel.max()
            mask = np.dstack([mask] * 3)
            img = (img * (0.4 + 0.6 * mask)).astype(np.uint8)

        return img

    # -----------------------------------------------------------------
    # Viewfinder Composition Overlays (Static Output)
    # -----------------------------------------------------------------
    def _draw_golden_spiral(self, canvas, color, thickness):
        """Dynamic golden spiral calculation that handles portrait, landscape, and arbitrary image ratios."""
        phi = 1.61803398875
        is_portrait = self.height > self.width

        if is_portrait:
            rect_w = self.width
            rect_h = int(rect_w * phi)
            if rect_h > self.height:
                rect_h = self.height
                rect_w = int(rect_h / phi)
        else:
            rect_h = self.height
            rect_w = int(rect_h * phi)
            if rect_w > self.width:
                rect_w = self.width
                rect_h = int(rect_w / phi)

        x_offset = (self.width - rect_w) // 2
        y_offset = (self.height - rect_h) // 2

        # Outer Bounding Rectangle
        cv2.rectangle(
            canvas,
            (x_offset, y_offset),
            (x_offset + rect_w, y_offset + rect_h),
            color,
            1,
        )

        x, y, w, h = x_offset, y_offset, rect_w, rect_h

        # Orientation-aware spiral sequence
        state = 0 if not is_portrait else 1

        for _ in range(8):
            if w <= 4 or h <= 4:
                break

            if state == 0:  # Cut left square
                s = min(h, w)
                cv2.line(canvas, (x + s, y), (x + s, y + h), color, 1)
                center = (x + s, y + h)
                cv2.ellipse(canvas, center, (s, s), 0, 180, 270, color, thickness)
                x += s
                w -= s

            elif state == 1:  # Cut top square
                s = min(w, h)
                cv2.line(canvas, (x, y + s), (x + w, y + s), color, 1)
                center = (x, y + s)
                cv2.ellipse(canvas, center, (s, s), 0, 270, 360, color, thickness)
                y += s
                h -= s

            elif state == 2:  # Cut right square
                s = min(h, w)
                cv2.line(canvas, (x + w - s, y), (x + w - s, y + h), color, 1)
                center = (x + w - s, y)
                cv2.ellipse(canvas, center, (s, s), 0, 0, 90, color, thickness)
                w -= s

            elif state == 3:  # Cut bottom square
                s = min(w, h)
                cv2.line(canvas, (x, y + h - s), (x + w, y + h - s), color, 1)
                center = (x + w, y + h - s)
                cv2.ellipse(canvas, center, (s, s), 0, 90, 180, color, thickness)
                h -= s

            state = (state + 1) % 4

    def draw_composition_guide(self, guide_type="Golden Spiral"):
        canvas = self.img.copy()
        color = (111, 200, 220)  # Hex #dcc86f in BGR
        thickness = 2

        if guide_type == "Rule of Thirds":
            h_step, w_step = self.height // 3, self.width // 3
            for i in (1, 2):
                cv2.line(canvas, (0, i * h_step), (self.width, i * h_step), color, thickness)
                cv2.line(canvas, (i * w_step, 0), (i * w_step, self.height), color, thickness)

        elif guide_type in ("Golden Spiral", "Golden Ratio"):
            self._draw_golden_spiral(canvas, color, thickness)

        elif guide_type == "Golden Triangles":
            cv2.line(canvas, (0, self.height), (self.width, 0), color, thickness)
            w_sq = float(self.width ** 2)
            h_sq = float(self.height ** 2)
            denom = w_sq + h_sq

            x_p1 = int((self.width * h_sq) / denom)
            y_p1 = int((w_sq * self.height) / denom)

            cv2.line(canvas, (0, 0), (x_p1, y_p1), color, thickness)
            cv2.line(canvas, (self.width, self.height), (self.width - x_p1, self.height - y_p1), color, thickness)

        elif guide_type == "Golden Ratio Grid":
            phi = 1.618
            w_ratio = int(self.width / (1 + phi))
            h_ratio = int(self.height / (1 + phi))

            cv2.line(canvas, (w_ratio, 0), (w_ratio, self.height), color, thickness)
            cv2.line(canvas, (self.width - w_ratio, 0), (self.width - w_ratio, self.height), color, thickness)
            cv2.line(canvas, (0, h_ratio), (self.width, h_ratio), color, thickness)
            cv2.line(canvas, (0, self.height - h_ratio), (self.width, h_ratio), color, thickness)

        elif guide_type == "Golden Section":
            x1, x2 = int(self.width * 0.382), int(self.width * 0.618)
            y1, y2 = int(self.height * 0.382), int(self.height * 0.618)

            cv2.line(canvas, (x1, 0), (x1, self.height), color, thickness)
            cv2.line(canvas, (x2, 0), (x2, self.height), color, thickness)
            cv2.line(canvas, (0, y1), (self.width, y1), color, thickness)
            cv2.line(canvas, (0, y2), (self.width, y2), color, thickness)

        return canvas
