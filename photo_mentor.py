"""
photo_mentor.py
----------------
Core image-analysis engine for Golden Number.

Given a photo, PhotoMentor can:
  1. Diagnose exposure, composition (horizon tilt), sharpness, and color
     saturation.
  2. Draw composition guide overlays: Rule of Thirds, Golden Ratio Grid,
     Golden Triangle, and Golden Spiral.
  3. Auto-correct each flaw individually (for before/after comparisons).
  4. Produce one final image with every needed correction applied.
"""

import cv2
import numpy as np

# Brand color (#dcc86f) as BGR, since OpenCV uses BGR ordering
GUIDE_COLOR_BGR = (111, 200, 220)


class PhotoMentor:
    """Runs a set of computer-vision checks and corrections on a single photo."""

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

    # ==================================================================
    # DIAGNOSTICS
    # ==================================================================

    def analyze_exposure(self):
        """Returns (grade, advice, avg_brightness)."""
        avg_brightness = float(np.mean(self.gray))
        overexposed_ratio = float(np.sum(self.gray > 240)) / self.gray.size

        if overexposed_ratio > 0.10:
            grade = "Overexposed"
            advice = "Highlights are clipped in a large part of the frame. Try lowering exposure compensation or using a faster shutter speed."
        elif avg_brightness < 60:
            grade = "Underexposed"
            advice = "The image is quite dark. Try raising ISO, opening up the aperture, or using a slower shutter speed."
        elif 100 <= avg_brightness <= 160:
            grade = "Well exposed"
            advice = "Brightness is well balanced, with good detail in both shadows and highlights."
        else:
            grade = "Acceptable exposure"
            advice = "Exposure is reasonable but not ideal — check the histogram for room to improve."

        return grade, advice, avg_brightness

    def analyze_composition(self):
        """Returns (grade, advice, tilt_degrees)."""
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
            direction = "clockwise (right side down)" if max_tilt > 0 else "counter-clockwise (left side down)"
            grade = "Tilted"
            advice = f"The horizon appears tilted about {abs(max_tilt):.1f}° {direction}. Consider rotating to level it."
        else:
            grade = "Level"
            advice = "No significant tilt detected — the horizon looks level."

        return grade, advice, max_tilt

    def analyze_sharpness(self):
        """Returns (grade, advice, sharpness_score)."""
        sharpness = cv2.Laplacian(self.gray, cv2.CV_64F).var()

        if sharpness < 100:
            grade = "Possibly blurry"
            advice = "Detail looks soft — this can happen from camera shake or missed focus. Try a faster shutter speed or a tripod."
        elif sharpness < 500:
            grade = "Acceptably sharp"
            advice = "Sharpness is reasonable for most uses."
        else:
            grade = "Very sharp"
            advice = "Excellent detail retention."

        return grade, advice, sharpness

    def analyze_saturation(self):
        """Returns (grade, advice, avg_saturation)."""
        avg_saturation = float(np.mean(self.hsv[:, :, 1]))

        if avg_saturation < 30:
            grade = "Washed out"
            advice = "Colors look pale. Try increasing saturation/contrast in editing, or check for haze."
        elif avg_saturation > 200:
            grade = "Oversaturated"
            advice = "Colors are very intense — watch out for unnatural skin tones or clipped color channels."
        else:
            grade = "Natural"
            advice = "Color intensity looks natural and well balanced."

        return grade, advice, avg_saturation

    def full_report(self):
        exp_grade, exp_advice, brightness = self.analyze_exposure()
        comp_grade, comp_advice, tilt = self.analyze_composition()
        sharp_grade, sharp_advice, sharpness = self.analyze_sharpness()
        sat_grade, sat_advice, saturation = self.analyze_saturation()

        report_lines = [
            "=" * 50,
            "Golden Number — Diagnostic Report",
            f"File: {self.image_path}",
            "=" * 50,
            "",
            f"1) Exposure: {exp_grade}  (avg brightness: {brightness:.1f} / 255)",
            f"   -> {exp_advice}",
            "",
            f"2) Composition: {comp_grade}  (tilt: {tilt:.1f}°)",
            f"   -> {comp_advice}",
            "",
            f"3) Sharpness: {sharp_grade}  (score: {sharpness:.1f})",
            f"   -> {sharp_advice}",
            "",
            f"4) Color Saturation: {sat_grade}  (avg saturation: {saturation:.1f} / 255)",
            f"   -> {sat_advice}",
            "=" * 50,
        ]
        return "\n".join(report_lines)

    # ==================================================================
    # COMPOSITION GUIDE OVERLAYS
    # ==================================================================

    @staticmethod
    def _draw_guide_line(canvas, pt1, pt2, thickness=2):
        """Draws a line with a subtle dark outline so it's visible on any background."""
        cv2.line(canvas, pt1, pt2, (0, 0, 0), thickness + 2, cv2.LINE_AA)
        cv2.line(canvas, pt1, pt2, GUIDE_COLOR_BGR, thickness, cv2.LINE_AA)

    @staticmethod
    def _draw_guide_arc(canvas, center, radius, start_angle, end_angle, thickness=2):
        cv2.ellipse(canvas, center, (radius, radius), 0, start_angle, end_angle,
                    (0, 0, 0), thickness + 2, cv2.LINE_AA)
        cv2.ellipse(canvas, center, (radius, radius), 0, start_angle, end_angle,
                    GUIDE_COLOR_BGR, thickness, cv2.LINE_AA)

    def draw_rule_of_thirds(self):
        """Classic rule-of-thirds grid: divides the frame into equal thirds."""
        canvas = self.img.copy()
        h_step = self.height / 3
        w_step = self.width / 3
        for i in (1, 2):
            y = int(i * h_step)
            x = int(i * w_step)
            self._draw_guide_line(canvas, (0, y), (self.width, y))
            self._draw_guide_line(canvas, (x, 0), (x, self.height))
        return canvas

    def draw_golden_ratio_grid(self):
        """Like rule of thirds, but divided at the golden ratio (~38.2% / 61.8%)."""
        canvas = self.img.copy()
        for frac in (0.382, 0.618):
            y = int(self.height * frac)
            x = int(self.width * frac)
            self._draw_guide_line(canvas, (0, y), (self.width, y))
            self._draw_guide_line(canvas, (x, 0), (x, self.height))
        return canvas

    @staticmethod
    def _foot_of_perpendicular(point, line_a, line_b):
        """Projects `point` onto the line through line_a/line_b and returns the foot."""
        a = np.array(line_a, dtype=float)
        b = np.array(line_b, dtype=float)
        p = np.array(point, dtype=float)
        ab = b - a
        t = np.dot(p - a, ab) / np.dot(ab, ab)
        foot = a + t * ab
        return (int(foot[0]), int(foot[1]))

    def draw_golden_triangle(self, variant="tl-br"):
        """
        Golden triangle guide: a diagonal across the frame plus two lines
        dropped perpendicular from the other corners onto that diagonal.

        variant: "tl-br" (diagonal from top-left to bottom-right) or
                 "tr-bl" (diagonal from top-right to bottom-left)
        """
        canvas = self.img.copy()
        w, h = self.width, self.height

        if variant == "tr-bl":
            a, b = (w, 0), (0, h)
            others = [(0, 0), (w, h)]
        else:
            a, b = (0, 0), (w, h)
            others = [(w, 0), (0, h)]

        self._draw_guide_line(canvas, a, b)
        for corner in others:
            foot = self._foot_of_perpendicular(corner, a, b)
            self._draw_guide_line(canvas, corner, foot)

        return canvas

    def draw_golden_spiral(self, iterations=9):
        """
        Golden (Fibonacci) spiral: repeatedly cuts the largest possible square
        from the current rectangle and draws a quarter-circle arc in it.
        """
        canvas = self.img.copy()
        x, y, cw, ch = 0, 0, self.width, self.height
        direction = 0

        for _ in range(iterations):
            side = min(cw, ch)
            if side < 8:
                break

            if direction == 0:
                sq_x, sq_y = x, y
                x += side
                cw -= side
                center = (sq_x + side, sq_y + side)
                start, end = 180, 270
            elif direction == 1:
                sq_x, sq_y = x, y
                y += side
                ch -= side
                center = (sq_x, sq_y + side)
                start, end = 270, 360
            elif direction == 2:
                sq_x, sq_y = x + cw - side, y
                cw -= side
                center = (sq_x, sq_y)
                start, end = 0, 90
            else:
                sq_x, sq_y = x, y + ch - side
                ch -= side
                center = (sq_x + side, sq_y)
                start, end = 90, 180

            self._draw_guide_arc(canvas, center, side, start, end)
            direction = (direction + 1) % 4

        return canvas

    GUIDE_OPTIONS = {
        "Rule of Thirds": "draw_rule_of_thirds",
        "Golden Ratio Grid": "draw_golden_ratio_grid",
        "Golden Triangle": "draw_golden_triangle",
        "Golden Spiral": "draw_golden_spiral",
    }

    def draw_guide(self, name, **kwargs):
        """Dispatch helper: draw_guide('Golden Triangle', variant='tr-bl')."""
        method_name = self.GUIDE_OPTIONS.get(name)
        if method_name is None:
            raise ValueError(f"Unknown guide: {name}")
        return getattr(self, method_name)(**kwargs)

    # ==================================================================
    # AUTO-CORRECTIONS (for before/after comparisons)
    # ==================================================================

    def fix_exposure(self, source=None):
        """Contrast-corrects and rebalances brightness toward a mid-gray target."""
        working = self.img.copy() if source is None else source.copy()

        lab = cv2.cvtColor(working, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_channel = clahe.apply(l_channel)
        working = cv2.cvtColor(cv2.merge((l_channel, a_channel, b_channel)), cv2.COLOR_LAB2BGR)

        avg_brightness = float(np.mean(cv2.cvtColor(working, cv2.COLOR_BGR2GRAY)))
        beta = float(np.clip(130 - avg_brightness, -80, 80))
        working = cv2.convertScaleAbs(working, alpha=1.0, beta=beta)
        return working

    def fix_composition(self, source=None):
        """Rotates the image to level a tilted horizon."""
        working = self.img.copy() if source is None else source.copy()
        _, _, tilt = self.analyze_composition()

        if abs(tilt) < 0.5:
            return working

        center = (self.width // 2, self.height // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, tilt, 1.0)
        working = cv2.warpAffine(
            working, rotation_matrix, (self.width, self.height),
            borderMode=cv2.BORDER_REPLICATE
        )
        return working

    def fix_sharpness(self, source=None):
        """Applies an unsharp mask to recover perceived detail."""
        working = self.img.copy() if source is None else source.copy()
        blurred = cv2.GaussianBlur(working, (0, 0), sigmaX=3)
        working = cv2.addWeighted(working, 1.5, blurred, -0.5, 0)
        return working

    def fix_saturation(self, source=None):
        """Scales color saturation toward a natural target level."""
        working = self.img.copy() if source is None else source.copy()
        hsv = cv2.cvtColor(working, cv2.COLOR_BGR2HSV).astype(np.float32)
        avg_sat = float(np.mean(hsv[:, :, 1]))

        target = 120.0
        scale = 1.0 if avg_sat < 1 else float(np.clip(target / avg_sat, 0.5, 2.0))
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * scale, 0, 255)
        working = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        return working

    def generate_final_image(self):
        """
        Applies every correction that's actually needed, in sequence, and
        returns one fully touched-up image.
        """
        working = self.img.copy()

        exp_grade, _, _ = self.analyze_exposure()
        comp_grade, _, _ = self.analyze_composition()
        sharp_grade, _, _ = self.analyze_sharpness()
        sat_grade, _, _ = self.analyze_saturation()

        if comp_grade == "Tilted":
            working = self.fix_composition(source=working)

        if exp_grade in ("Overexposed", "Underexposed"):
            working = self.fix_exposure(source=working)

        if sharp_grade == "Possibly blurry":
            working = self.fix_sharpness(source=working)

        if sat_grade in ("Washed out", "Oversaturated"):
            working = self.fix_saturation(source=working)

        return working
