"""
photo_mentor.py
----------------
Core analysis, composition guides (Golden Spiral, Golden Triangles, etc.),
aspect ratio conforming, and image correction logic tailored for photographer presets.
"""

import cv2
import numpy as np

PHI = 1.61803398875


class PhotoMentor:
    """Runs computer-vision checks and applies automatic fixes to photos."""

    def __init__(self, image_path: str, target_aspect_ratio_str: str = None):
        self.image_path = image_path
        self.img = cv2.imread(image_path)
        if self.img is None:
            raise FileNotFoundError(
                f"Could not read image at '{image_path}'. "
                "Check the path and make sure it's a valid image file."
            )

        # Conform image aspect ratio to photographer preset if provided
        if target_aspect_ratio_str:
            self.img = self._crop_to_aspect_ratio(self.img, target_aspect_ratio_str)

        self.gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        self.hsv = cv2.cvtColor(self.img, cv2.COLOR_BGR2HSV)
        self.height, self.width = self.gray.shape

    # -----------------------------------------------------------------
    # Aspect Ratio Conforming Engine
    # -----------------------------------------------------------------
    def _crop_to_aspect_ratio(self, img, aspect_ratio_str: str):
        """Center-crops the image to match a target aspect ratio string (e.g., '4 / 3', '1 / 1')."""
        try:
            num, den = aspect_ratio_str.split("/")
            target_ratio = float(num.strip()) / float(den.strip())
        except Exception:
            return img

        h, w = img.shape[:2]
        current_ratio = w / h

        if abs(current_ratio - target_ratio) < 0.01:
            return img  # Already matching ratio

        if current_ratio > target_ratio:
            # Image is wider than target -> Crop sides
            new_w = int(h * target_ratio)
            offset = (w - new_w) // 2
            return img[:, offset:offset + new_w]
        else:
            # Image is taller than target -> Crop top/bottom
            new_h = int(w / target_ratio)
            offset = (h - new_h) // 2
            return img[offset:offset + new_h, :]

    # -----------------------------------------------------------------
    # Metric Analysis & Individual Style-Aware Fixes
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

    def fix_exposure(self, img_bgr=None, style_config=None):
        src = self.img if img_bgr is None else img_bgr
        gray_src = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
        avg_brightness = float(np.mean(gray_src))
        overexposed_ratio = float(np.sum(gray_src > 240)) / gray_src.size

        contrast_mod = style_config.get("contrast_factor", 1.0) if style_config else 1.0
        target_brightness = (110.0 if overexposed_ratio > 0.10 else 128.0) * (2.0 - contrast_mod * 0.8)

        if avg_brightness < 1.0:
            avg_brightness = 1.0

        gamma = np.clip(target_brightness / avg_brightness, 0.70, 1.35)
        inv_gamma = 1.0 / gamma
        table = np.array(
            [((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]
        ).astype("uint8")

        adjusted = cv2.LUT(src, table)
        return cv2.addWeighted(src, 0.50, adjusted, 0.50, 0)

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

    def fix_sharpness(self, img_bgr=None, style_config=None):
        src = self.img if img_bgr is None else img_bgr
        grade, _, _ = self.analyze_sharpness()

        sharp_factor = 1.25 if style_config and style_config.get("grain", False) else 1.15
        blurred = cv2.GaussianBlur(src, (0, 0), 2.0)
        return cv2.addWeighted(src, sharp_factor, blurred, -(sharp_factor - 1.0), 0)

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

    def fix_saturation(self, img_bgr=None, style_config=None):
        src = self.img if img_bgr is None else img_bgr

        if style_config and style_config.get("monochrome", False):
            gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
            return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        hsv = cv2.cvtColor(src, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        target_mult = style_config.get("saturation_factor", 1.0) if style_config else 1.0
        s = np.clip(s.astype(np.float32) * target_mult, 0, 255).astype(np.uint8)

        fixed_hsv = cv2.merge((h, s, v))
        return cv2.cvtColor(fixed_hsv, cv2.COLOR_HSV2BGR)

    def generate_master_fixed_image(self, style_config=None):
        fixed = self.fix_exposure(self.img, style_config)
        fixed = self.fix_composition(fixed)
        fixed = self.fix_sharpness(fixed, style_config)
        fixed = self.fix_saturation(fixed, style_config)
        return fixed

    # -----------------------------------------------------------------
    # Photographer Style Transfer Engine
    # -----------------------------------------------------------------
    def apply_photographer_style(self, base_image, style_config):
        img = base_image.copy().astype(np.float32)

        contrast = style_config.get("contrast_factor", 1.0)
        sat_mult = style_config.get("saturation_factor", 1.0)
        monochrome = style_config.get("monochrome", False)
        grain = style_config.get("grain", False)
        vignette = style_config.get("vignette", False)
        warmth = style_config.get("warmth", 0.0)
        cool_shadows = style_config.get("cool_shadows", False)

        # 1. Contrast & Tonal Tints
        img = (img - 127.5) * contrast + 127.5
        if warmth != 0.0:
            img[:, :, 2] += warmth * 15
            img[:, :, 0] -= warmth * 10

        if cool_shadows:
            shadow_mask = np.clip((128.0 - img) / 128.0, 0, 1)
            img[:, :, 0] += shadow_mask[:, :, 0] * 18.0

        img = np.clip(img, 0, 255).astype(np.uint8)

        # 2. Saturation & Monochrome
        if monochrome:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        elif sat_mult != 1.0:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * sat_mult, 0, 255)
            img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # 3. Film Grain
        if grain:
            noise = np.random.normal(0, 12, img.shape).astype(np.float32)
            img = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        # 4. Vignette Effect
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
    # Colorblind-Friendly Correction (Daltonization)
    # -----------------------------------------------------------------
    # Full-severity CVD simulation matrices (Machado, Oliveira & Fernandes,
    # "A Physiologically-based Model for Simulation of Color Vision
    # Deficiency", 2009), applied directly to linear (gamma-decoded) RGB.
    # A naive single linear projection in LMS space (the more commonly seen
    # "textbook" approach) works reasonably for protanopia/deuteranopia but
    # sends a large fraction of tritanopia's simulated colors wildly outside
    # the visible RGB gamut, producing distorted, neon-looking results once
    # clipped. These matrices are fit to stay within gamut for all three
    # types, including tritanopia.
    _CB_SIM_RGB = {
        "protanopia": np.array([
            [0.152286, 1.052583, -0.204868],
            [0.114503, 0.786281, 0.099216],
            [-0.003882, -0.048116, 1.051998],
        ]),
        "deuteranopia": np.array([
            [0.367322, 0.860646, -0.227968],
            [0.280085, 0.672501, 0.047413],
            [-0.011820, 0.042940, 0.968881],
        ]),
        "tritanopia": np.array([
            [1.255528, -0.076749, -0.178779],
            [-0.078411, 0.930809, 0.147602],
            [0.004733, 0.691367, 0.303900],
        ]),
    }

    @staticmethod
    def _srgb_to_linear(rgb_uint8):
        x = rgb_uint8.astype(np.float32) / 255.0
        return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)

    @staticmethod
    def _linear_to_srgb(linear):
        x = np.clip(linear, 0, 1)
        out = np.where(x <= 0.0031308, x * 12.92, 1.055 * (x ** (1 / 2.4)) - 0.055)
        return np.clip(out * 255, 0, 255).astype(np.uint8)

    def apply_colorblind_correction(self, img_bgr=None, cb_type="deuteranopia", strength=1.0):
        """
        Daltonizes the image: simulates how it would look to someone with the
        given color-vision-deficiency type, computes what color information
        that simulation loses, then redistributes that lost information into
        channels the viewer can still perceive. Supports the three most common
        dichromatic types: protanopia, deuteranopia (most common), and
        tritanopia.
        """
        src = self.img if img_bgr is None else img_bgr
        matrix = self._CB_SIM_RGB.get(cb_type, self._CB_SIM_RGB["deuteranopia"])

        rgb = cv2.cvtColor(src, cv2.COLOR_BGR2RGB)
        linear = self._srgb_to_linear(rgb)
        flat = linear.reshape(-1, 3).T  # 3 x N
        sim_linear = (matrix @ flat).T.reshape(linear.shape)

        # Error = the color information lost in simulation.
        error = linear - sim_linear
        correction = np.zeros_like(error)
        correction[:, :, 1] = error[:, :, 0] * 0.7 + error[:, :, 1]
        correction[:, :, 2] = error[:, :, 0] * 0.7 + error[:, :, 2]

        corrected_linear = np.clip(linear + correction * strength, 0, 1)
        corrected_rgb = self._linear_to_srgb(corrected_linear)
        return cv2.cvtColor(corrected_rgb, cv2.COLOR_RGB2BGR)

    def simulate_colorblindness(self, img_bgr=None, cb_type="deuteranopia"):
        """
        Returns how the image would look to someone with the given dichromatic
        color-vision-deficiency type — no correction applied. Useful for
        showing a person what a given CVD type actually does to an image
        (e.g. a sample color wheel) before/alongside offering the correction.
        """
        src = self.img if img_bgr is None else img_bgr
        matrix = self._CB_SIM_RGB.get(cb_type, self._CB_SIM_RGB["deuteranopia"])

        rgb = cv2.cvtColor(src, cv2.COLOR_BGR2RGB)
        linear = self._srgb_to_linear(rgb)
        flat = linear.reshape(-1, 3).T
        sim_linear = (matrix @ flat).T.reshape(linear.shape)
        sim_rgb = self._linear_to_srgb(sim_linear)

        return cv2.cvtColor(sim_rgb, cv2.COLOR_RGB2BGR)

    # -----------------------------------------------------------------
    # Visual-Attention / Contrast Heatmap
    # -----------------------------------------------------------------
    def generate_attention_heatmap(self, img_bgr=None, blend_alpha=0.55):
        """
        Produces a heatmap approximating which areas of the photo draw the eye
        most, combining local contrast, edge strength, and color saturation
        (a fast, dependency-free stand-in for a full saliency model). Returns
        (overlay_bgr, raw_saliency_uint8).
        """
        src = self.img if img_bgr is None else img_bgr
        gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY).astype(np.float32)

        # Local contrast: difference from a heavily blurred version of itself.
        blurred = cv2.GaussianBlur(gray, (0, 0), sigmaX=15)
        local_contrast = np.abs(gray - blurred)

        # Edge / gradient strength.
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        edge_strength = cv2.magnitude(gx, gy)

        # Color saturation (vivid colors pull the eye).
        hsv = cv2.cvtColor(src, cv2.COLOR_BGR2HSV).astype(np.float32)
        sat = hsv[:, :, 1]

        saliency = (
            0.45 * cv2.normalize(local_contrast, None, 0, 1, cv2.NORM_MINMAX) +
            0.40 * cv2.normalize(edge_strength, None, 0, 1, cv2.NORM_MINMAX) +
            0.15 * cv2.normalize(sat, None, 0, 1, cv2.NORM_MINMAX)
        )
        saliency = cv2.GaussianBlur(saliency, (0, 0), sigmaX=6)
        saliency_u8 = np.clip(saliency * 255, 0, 255).astype(np.uint8)

        heat_color = cv2.applyColorMap(saliency_u8, cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(src, 1 - blend_alpha, heat_color, blend_alpha, 0)
        return overlay, saliency_u8

    # -----------------------------------------------------------------
    # Viewfinder Composition Overlays
    # -----------------------------------------------------------------
    @staticmethod
    def golden_spiral_svg_geometry(vb_w, vb_h, iterations=10):
        """
        Computes the nested Fibonacci sub-squares and the connecting spiral
        arc for an SVG canvas of size (vb_w, vb_h). Returns a dict with
        'squares' (list of (x, y, w, h) rects, largest first) and 'path' (an
        SVG path 'd' string for the spiral curve). Shared by both the live
        camera viewfinder and the "Explain Guide" popup so the overlay is
        always geometrically correct and consistent between the two.
        """
        is_portrait = vb_h > vb_w

        if is_portrait:
            rect_w = vb_w
            rect_h = rect_w * PHI
            if rect_h > vb_h:
                rect_h = vb_h
                rect_w = rect_h / PHI
        else:
            rect_h = vb_h
            rect_w = rect_h * PHI
            if rect_w > vb_w:
                rect_w = vb_w
                rect_h = rect_w / PHI

        x_offset = (vb_w - rect_w) / 2
        y_offset = (vb_h - rect_h) / 2

        x, y, w, h = x_offset, y_offset, rect_w, rect_h
        state = 0 if not is_portrait else 1

        squares = [(x_offset, y_offset, rect_w, rect_h)]
        path_cmds = []
        first = True

        for _ in range(iterations):
            if w <= 2 or h <= 2:
                break

            if state == 0:
                s = min(h, w)
                cx, cy, r = x + s, y + h, s
                start_angle, end_angle = 180, 270
                x += s
                w -= s
            elif state == 1:
                s = min(w, h)
                cx, cy, r = x, y + s, s
                start_angle, end_angle = 270, 360
                y += s
                h -= s
            elif state == 2:
                s = min(h, w)
                cx, cy, r = x + w - s, y, s
                start_angle, end_angle = 0, 90
                w -= s
            else:
                s = min(w, h)
                cx, cy, r = x + w, y + h - s, s
                start_angle, end_angle = 90, 180
                h -= s

            squares.append((x, y, w, h))

            start_x = cx + r * np.cos(np.radians(start_angle))
            start_y = cy + r * np.sin(np.radians(start_angle))
            end_x = cx + r * np.cos(np.radians(end_angle))
            end_y = cy + r * np.sin(np.radians(end_angle))

            if first:
                path_cmds.append(f"M {start_x:.2f},{start_y:.2f}")
                first = False
            path_cmds.append(f"A {r:.2f},{r:.2f} 0 0,1 {end_x:.2f},{end_y:.2f}")

            state = (state + 1) % 4

        return {"squares": squares, "path": " ".join(path_cmds)}

    def _draw_golden_spiral(self, canvas, color, thickness):
        geometry = self.golden_spiral_svg_geometry(self.width, self.height)

        for (sx, sy, sw, sh) in geometry["squares"]:
            cv2.rectangle(
                canvas,
                (int(sx), int(sy)),
                (int(sx + sw), int(sy + sh)),
                color,
                1,
            )

        # Rasterize the spiral path (a sequence of "M"/"A" commands) as an
        # explicit polyline of small arc segments for cv2 drawing.
        pts = []
        for cmd in geometry["path"].split(" A "):
            cmd = cmd.strip()
            if cmd.startswith("M "):
                x_str, y_str = cmd[2:].split(",")
                pts.append((float(x_str), float(y_str)))
            else:
                parts = cmd.replace(",", " ").split()
                # r r 0 0 1 x y
                end_x, end_y = float(parts[-2]), float(parts[-1])
                pts.append((end_x, end_y))

        for i in range(len(pts) - 1):
            cv2.line(
                canvas,
                (int(pts[i][0]), int(pts[i][1])),
                (int(pts[i + 1][0]), int(pts[i + 1][1])),
                color,
                thickness,
            )

    def draw_composition_guide(self, guide_type="Golden Spiral"):
        canvas = self.img.copy()
        color = (111, 200, 220)
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
