"""
photo_mentor.py
----------------
A starter "AI photography mentor" script.

Given a photo, it analyzes:
  1. Exposure (is it too bright / too dark?)
  2. Composition (is the horizon tilted?)
  3. Sharpness (is it blurry?)
  4. Color saturation (are colors washed out or oversaturated?)

...and prints a plain-English diagnostic report.

Usage:
    python photo_mentor.py path/to/photo.jpg

Install dependencies first:
    pip install opencv-python numpy
"""

import sys
import cv2
import numpy as np


class PhotoMentor:
    """Runs a set of computer-vision checks on a single photo."""

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
        """Returns (grade, advice) based on average brightness and highlight clipping."""
        avg_brightness = float(np.mean(self.gray))

        # Fraction of pixels that are essentially blown-out white (0.0 - 1.0)
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

    # ------------------------------------------------------------------
    # 2. Composition (horizon tilt)
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
                # Only consider lines that are roughly horizontal (candidates for a horizon)
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

    # ------------------------------------------------------------------
    # 3. Sharpness
    # ------------------------------------------------------------------
    def analyze_sharpness(self):
        """Uses the variance of the Laplacian as a focus/blur measure."""
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

    # ------------------------------------------------------------------
    # 4. Color saturation
    # ------------------------------------------------------------------
    def analyze_saturation(self):
        """Checks average saturation in HSV space."""
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

    # ------------------------------------------------------------------
    # Full report
    # ------------------------------------------------------------------
    def full_report(self):
        exp_grade, exp_advice, brightness = self.analyze_exposure()
        comp_grade, comp_advice, tilt = self.analyze_composition()
        sharp_grade, sharp_advice, sharpness = self.analyze_sharpness()
        sat_grade, sat_advice, saturation = self.analyze_saturation()

        report_lines = [
            "=" * 50,
            f"AI Photography Mentor — Diagnostic Report",
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

    def draw_rule_of_thirds(self):
        """Returns a copy of the image with rule-of-thirds gridlines drawn on it."""
        canvas = self.img.copy()
        h_step = self.height // 3
        w_step = self.width // 3
        color = (255, 255, 0)  # cyan in BGR
        thickness = 2
        for i in (1, 2):
            cv2.line(canvas, (0, i * h_step), (self.width, i * h_step), color, thickness)
            cv2.line(canvas, (i * w_step, 0), (i * w_step, self.height), color, thickness)
        return canvas


def main():
    if len(sys.argv) < 2:
        print("Usage: python photo_mentor.py path/to/photo.jpg")
        sys.exit(1)

    image_path = sys.argv[1]

    try:
        mentor = PhotoMentor(image_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(mentor.full_report())

    # Optional: save a version of the photo with rule-of-thirds guide lines
    preview = mentor.draw_rule_of_thirds()
    output_path = "rule_of_thirds_preview.jpg"
    cv2.imwrite(output_path, preview)
    print(f"\nSaved a rule-of-thirds guide overlay to: {output_path}")


if __name__ == "__main__":
    main()
