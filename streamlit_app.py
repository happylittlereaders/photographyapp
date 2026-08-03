"""
streamlit_app.py
-----------------
Golden Number — a web app that analyzes a photo and shows classic
composition guides (Rule of Thirds, Golden Ratio Grid, Golden Triangle,
Golden Spiral), diagnoses exposure/sharpness/color issues, auto-corrects
each one with a before/after comparison, and produces a final touched-up
image.

Run locally with:
    pip install -r requirements.txt
    streamlit run streamlit_app.py

Deploy for free at https://share.streamlit.io (Streamlit Community Cloud)
by connecting your GitHub repo.
"""

import cv2
import numpy as np
import streamlit as st
from PIL import Image

from photo_mentor import PhotoMentor

BRAND_COLOR = "#dcc86f"

st.set_page_config(page_title="Golden Number", page_icon="🔱", layout="wide")

# ----------------------------------------------------------------------
# Brand styling
# ----------------------------------------------------------------------
st.markdown(
    f"""
    <style>
    h1, h2, h3 {{
        color: {BRAND_COLOR};
    }}
    .stButton > button, .stDownloadButton > button {{
        background-color: {BRAND_COLOR};
        color: #1a1a1a;
        border: none;
        font-weight: 600;
    }}
    .stButton > button:hover, .stDownloadButton > button:hover {{
        background-color: #c9b45c;
        color: #1a1a1a;
    }}
    [data-testid="stFileUploaderDropzone"] {{
        border-color: {BRAND_COLOR} !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🔱 Golden Number")
st.write(
    "Upload a photo to see classic composition guides overlaid on it, "
    "get an instant diagnostic report, and preview auto-corrected fixes "
    "for anything that isn't quite right."
)


def to_pil(bgr_image):
    """Convert an OpenCV BGR array to a PIL RGB image for display in Streamlit."""
    return Image.fromarray(cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB))


uploaded_file = st.file_uploader(
    "Upload a photo", type=["jpg", "jpeg", "png"], accept_multiple_files=False
)

if uploaded_file is not None:
    pil_image = Image.open(uploaded_file).convert("RGB")
    rgb_array = np.array(pil_image)
    bgr_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)

    temp_path = "temp_upload.jpg"
    cv2.imwrite(temp_path, bgr_array)

    mentor = PhotoMentor(temp_path)

    exp_grade, exp_advice, brightness = mentor.analyze_exposure()
    comp_grade, comp_advice, tilt = mentor.analyze_composition()
    sharp_grade, sharp_advice, sharpness = mentor.analyze_sharpness()
    sat_grade, sat_advice, saturation = mentor.analyze_saturation()

    st.subheader("Your Photo")
    st.image(pil_image, use_container_width=True)

    # ------------------------------------------------------------------
    # Composition guide overlays
    # ------------------------------------------------------------------
    st.header("Composition Guides")

    guide_names = list(PhotoMentor.GUIDE_OPTIONS.keys())
    selected_guides = st.multiselect(
        "Choose which guides to overlay", guide_names, default=guide_names
    )

    triangle_variant = "tl-br"
    if "Golden Triangle" in selected_guides:
        triangle_variant = st.radio(
            "Golden Triangle diagonal direction",
            options=["tl-br", "tr-bl"],
            format_func=lambda v: "Top-left \u2192 Bottom-right" if v == "tl-br" else "Top-right \u2192 Bottom-left",
            horizontal=True,
        )

    if selected_guides:
        guide_cols = st.columns(min(2, len(selected_guides)))
        for i, guide_name in enumerate(selected_guides):
            kwargs = {"variant": triangle_variant} if guide_name == "Golden Triangle" else {}
            overlay = mentor.draw_guide(guide_name, **kwargs)
            with guide_cols[i % len(guide_cols)]:
                st.image(to_pil(overlay), caption=guide_name, use_container_width=True)
    else:
        st.info("Select at least one guide above to see it overlaid on your photo.")

    # ------------------------------------------------------------------
    # Diagnostic report + before/after fixes
    # ------------------------------------------------------------------
    st.header("Diagnostic Report")

    checks = [
        {
            "title": "Exposure",
            "grade": exp_grade,
            "advice": exp_advice,
            "metric_label": "Avg brightness (0-255)",
            "metric_value": brightness,
            "is_issue": exp_grade in ("Overexposed", "Underexposed"),
            "fix_fn": mentor.fix_exposure,
        },
        {
            "title": "Composition",
            "grade": comp_grade,
            "advice": comp_advice,
            "metric_label": "Tilt (degrees)",
            "metric_value": tilt,
            "is_issue": comp_grade == "Tilted",
            "fix_fn": mentor.fix_composition,
        },
        {
            "title": "Sharpness",
            "grade": sharp_grade,
            "advice": sharp_advice,
            "metric_label": "Sharpness score",
            "metric_value": sharpness,
            "is_issue": sharp_grade == "Possibly blurry",
            "fix_fn": mentor.fix_sharpness,
        },
        {
            "title": "Color Saturation",
            "grade": sat_grade,
            "advice": sat_advice,
            "metric_label": "Avg saturation (0-255)",
            "metric_value": saturation,
            "is_issue": sat_grade in ("Washed out", "Oversaturated"),
            "fix_fn": mentor.fix_saturation,
        },
    ]

    for check in checks:
        st.subheader(f"{check['title']}: {check['grade']}")
        st.caption(f"{check['metric_label']}: {check['metric_value']:.1f}")
        st.write(check["advice"])

        if check["is_issue"]:
            fixed = check["fix_fn"]()
            before_col, after_col = st.columns(2)
            with before_col:
                st.image(pil_image, caption="Before", use_container_width=True)
            with after_col:
                st.image(to_pil(fixed), caption="After (auto-corrected)", use_container_width=True)
        else:
            st.success("This looks good already — no correction needed.")

        st.divider()

    # ------------------------------------------------------------------
    # Final combined image
    # ------------------------------------------------------------------
    st.header("Final Enhanced Photo")
    st.write("Every correction needed above, applied together in one image.")

    final_image = mentor.generate_final_image()
    final_col1, final_col2 = st.columns(2)
    with final_col1:
        st.image(pil_image, caption="Original", use_container_width=True)
    with final_col2:
        st.image(to_pil(final_image), caption="Final Enhanced", use_container_width=True)

    final_rgb = cv2.cvtColor(final_image, cv2.COLOR_BGR2RGB)
    is_success, buffer = cv2.imencode(".jpg", cv2.cvtColor(final_rgb, cv2.COLOR_RGB2BGR))
    if is_success:
        st.download_button(
            "Download final enhanced photo",
            data=buffer.tobytes(),
            file_name="golden_number_enhanced.jpg",
            mime="image/jpeg",
        )

else:
    st.info("Upload a JPG or PNG photo above to get started.")
