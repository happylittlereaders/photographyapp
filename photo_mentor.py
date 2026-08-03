"""
photo_mentor.py
----------------
Core analysis, composition guides (including Golden Spiral & Golden Triangles),
and auto-correction algorithms.
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

    # ------------------------------------------------------------------
    # 1. Exposure
    # ------------------------------------------------------------------
    def analyze_exposure(self):
        """Returns (grade, advice, avg_brightness) based on brightness & clipping."""
        avg_brightness = float(np.mean(self.gray))
        overexposed_ratio = float(np.sum(self.gray > 240)) / self.gray.size

        if overexposed_ratio > 0.10:
            grade = "Overexposed"
            advice = "Highlights are clipped in a large part of the frame. Lowering exposure helps restore lost detail."
        elif avg_brightness < 60:
            grade = "Underexposed"
            advice = "The image is quite dark. Brightening shadows and midtones will uncover hidden details."
        elif 100 <= avg_brightness <= 160:
            grade = "Well exposed"
            advice = "Brightness is well balanced, with good detail in both shadows and highlights."
        else:
            grade = "Acceptable exposure"
            advice = "Exposure is reasonable, but contrast and midtone balancing can improve it."

        return grade, advice, avg_brightness

    def fix_exposure(self, img_bgr=None):
        """Applies CLAHE to balance exposure."""
        src = self.img if img_bgr is None else img_bgr
        lab = cv2.cvtColor(src, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l_channel)

        merged = cv2.merge((cl, a_channel, b_channel))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    # ------------------------------------------------------------------
    # 2. Composition (Horizon Tilt)
    # ------------------------------------------------------------------
    def analyze_composition(self):
        """Detects dominant near-horizontal lines and estimates tilt angle."""
        edges = cv2.Canny(self.gray, 50, 150)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=100,
            minLineLength=self.width // 4, maxLineGap=10
        )

        max_tilt = 0.0
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
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
        """Rotates image to level horizon if tilt is detected."""
        src = self.img if img_bgr is None else img_bgr
        _, _, tilt = self.analyze_composition()

        if abs(tilt) <= 2:
            return src.copy()

        center = (self.width // 2, self.height // 2)
        matrix = cv2.getRotationMatrix2D(center, tilt, 1.0)
        return cv2.warpAffine(
            src, matrix, (self.width, self.height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )

    # ------------------------------------------------------------------
    # 3. Sharpness
    # ------------------------------------------------------------------
    def analyze_sharpness(self):
        """Uses variance of Laplacian to evaluate focus and blur."""
        sharpness = cv2.Laplacian(self.gray, cv2.CV_64F).var()

        if sharpness < 100:
            grade = "Possibly blurry"
            advice = "Detail looks soft. Applying subtle unsharp masking will enhance key edges."
        elif sharpness < 500:
            grade = "Acceptably sharp"
            advice = "Sharpness is reasonable for most uses."
        else:
            grade = "Very sharp"
            advice = "Excellent detail retention."

        return grade, advice, sharpness

    def fix_sharpness(self, img_bgr=None):
        """Applies unsharp masking filter to sharpen image."""
        src = self.img if img_bgr is None else img_bgr
        blurred = cv2.GaussianBlur(src, (0, 0), 3)
        return cv2.addWeighted(src, 1.5, blurred, -0.5, 0)

    # ------------------------------------------------------------------
    # 4. Color Saturation
    # ------------------------------------------------------------------
    def analyze_saturation(self):
        """Checks average saturation in HSV space."""
        avg_saturation = float(np.mean(self.hsv[:, :, 1]))

        if avg_saturation < 30:
            grade = "Washed out"
            advice = "Colors look pale. Boosting saturation will make the photo feel more vivid."
        elif avg_saturation > 200:
            grade = "Oversaturated"
            advice = "Colors are very intense. Tone down saturation slightly for a natural look."
        else:
            grade = "Natural"
            advice = "Color intensity looks natural and well balanced."

        return grade, advice, avg_saturation

    def fix_saturation(self, img_bgr=None):
        """Normalizes saturation towards healthy mean."""
        src = self.img if img_bgr is None else img_bgr
        hsv = cv2.cvtColor(src, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        avg_sat = np.mean(s)
        if avg_sat < 30:
            s = cv2.add(s, 35)
        elif avg_sat > 200:
            s = cv2.subtract(s, 30)

        fixed_hsv = cv2.merge((h, s, v))
        return cv2.cvtColor(fixed_hsv, cv2.COLOR_HSV2BGR)

    # ------------------------------------------------------------------
    # Master Fixed Output
    # ------------------------------------------------------------------
    def generate_master_fixed_image(self):
        """Applies all available fixes sequentially."""
        fixed = self.fix_exposure(self.img)
        fixed = self.fix_composition(fixed)
        fixed = self.fix_sharpness(fixed)
        fixed = self.fix_saturation(fixed)
        return fixed

    # ------------------------------------------------------------------
    # Composition Overlays
    # ------------------------------------------------------------------
    def draw_composition_guide(self, guide_type="Golden Spiral"):
        """Draws specified composition guide over image."""
        canvas = self.img.copy()
        color = (111, 200, 220)  # Hex #dcc86f in BGR
        thickness = 2

        if guide_type == "Rule of Thirds":
            h_step, w_step = self.height // 3, self.width // 3
            for i in (1, 2):
                cv2.line(canvas, (0, i * h_step), (self.width, i * h_step), color, thickness)
                cv2.line(canvas, (i * w_step, 0), (i * w_step, self.height), color, thickness)

        elif guide_type in ("Golden Spiral", "Golden Ratio"):
            # Golden Spiral (Fibonacci Spiral)
            x, y, w, h = 0, 0, self.width, self.height
            phi = 1.61803398875

            # Recursively subdivide golden rectangles and draw arcs
            # Directions: 0=Left arc, 1=Top arc, 2=Right arc, 3=Bottom arc
            direction = 0
            for _ in range(8):
                if w <= 2 or h <= 2:
                    break

                if direction == 0:  # Cut square from left
                    square_dim = int(h)
                    if square_dim > w: square_dim = w
                    # Draw square bounding box
                    cv2.rectangle(canvas, (x, y), (x + square_dim, y + h), color, 1)
                    # Draw Golden Arc
                    center = (x + square_dim, y + h)
                    cv2.ellipse(canvas, center, (square_dim, h), 0, 180, 270, color, thickness)
                    x += square_dim
                    w -= square_dim

                elif direction == 1:  # Cut square from top
                    square_dim = int(w)
                    if square_dim > h: square_dim = h
                    cv2.rectangle(canvas, (x, y), (x + w, y + square_dim), color, 1)
                    center = (x, y + square_dim)
                    cv2.ellipse(canvas, center, (w, square_dim), 0, 270, 360, color, thickness)
                    y += square_dim
                    h -= square_dim

                elif direction == 2:  # Cut square from right
                    square_dim = int(h)
                    if square_dim > w: square_dim = w
                    cv2.rectangle(canvas, (x + w - square_dim, y), (x + w, y + h), color, 1)
                    center = (x + w - square_dim, y)
                    cv2.ellipse(canvas, center, (square_dim, h), 0, 0, 90, color, thickness)
                    w -= square_dim

                elif direction == 3:  # Cut square from bottom
                    square_dim = int(w)
                    if square_dim > h: square_dim = h
                    cv2.rectangle(canvas, (x, y + h - square_dim), (x + w, y + h), color, 1)
                    center = (x + w, y + h - square_dim)
                    cv2.ellipse(canvas, center, (w, square_dim), 0, 90, 180, color, thickness)
                    h -= square_dim

                direction = (direction + 1) % 4

        elif guide_type == "Golden Triangles":
            # Main diagonal line from bottom-left to top-right
            cv2.line(canvas, (0, self.height), (self.width, 0), color, thickness)

            # Perpendicular lines meeting main diagonal at 90 degrees
            w_sq = float(self.width ** 2)
            h_sq = float(self.height ** 2)
            denom = w_sq + h_sq

            # Projection point from top-left (0, 0) onto diagonal
            x_p1 = int((self.width * h_sq) / denom)
            y_p1 = int((w_sq * self.height) / denom)

            # Draw perpendicular line from top-left to diagonal
            cv2.line(canvas, (0, 0), (x_p1, y_p1), color, thickness)

            # Draw perpendicular line from bottom-right to diagonal
            cv2.line(canvas, (self.width, self.height), (self.width - x_p1, self.height - y_p1), color, thickness)

        elif guide_type == "Golden Ratio Grid":
            phi = 1.618
            w_ratio = int(self.width / (1 + phi))
            h_ratio = int(self.height / (1 + phi))

            cv2.line(canvas, (w_ratio, 0), (w_ratio, self.height), color, thickness)
            cv2.line(canvas, (self.width - w_ratio, 0), (self.width - w_ratio, self.height), color, thickness)
            cv2.line(canvas, (0, h_ratio), (self.width, h_ratio), color, thickness)
            cv2.line(canvas, (0, self.height - h_ratio), (self.width, self.height - h_ratio), color, thickness)

        elif guide_type == "Golden Section":
            x1, x2 = int(self.width * 0.382), int(self.width * 0.618)
            y1, y2 = int(self.height * 0.382), int(self.height * 0.618)

            cv2.line(canvas, (x1, 0), (x1, self.height), color, thickness)
            cv2.line(canvas, (x2, 0), (x2, self.height), color, thickness)
            cv2.line(canvas, (0, y1), (self.width, y1), color, thickness)
            cv2.line(canvas, (0, y2), (self.width, y2), color, thickness)

        return canvas
