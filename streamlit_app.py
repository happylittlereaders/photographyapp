"""
streamlit_app.py
-----------------
A Streamlit web app version of the AI Photography Mentor with custom #dcc86f styling.
"""

import streamlit as st
import numpy as np
import cv2
from PIL import Image

from photo_mentor import PhotoMentor


st.set_page_config(page_title="AI Photography Mentor", page_icon="📷", layout="wide")

# Inject Custom CSS to make #dcc86f the dominant brand theme
st.markdown(
    """
    <style>
        /* Main Title & Header Accents */
        h1, h2, h3, .stAppHeader {
            color: #dcc86f !important;
        }

        /* Accent Borders and Focus Highlights */
        .stButton>button {
            border: 2px solid #dcc86f !important;
            color: #dcc86f !important;
            background-color: transparent !important;
            font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #dcc86f !important;
            color: #111111 !important;
        }

        /* Diagnostic Card Highlight Styling */
        div[data-testid="stVerticalBlock"] > div.element-container {
            border-left: 3px solid #dcc86f;
            padding-left: 10px;
        }

        /* Custom Badge / Pill Style for Grades */
        .grade-badge {
            background-color: #dcc86f;
            color: #111111;
            padding: 3px 10px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 0.9em;
        }

        /* Divider styling */
        hr {
            border-color: #dcc86f !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📷 AI Photography Mentor")
st.write(
    "Upload a photo and get instant feedback on exposure, composition, "
    "sharpness, and color — like a photography instructor reviewing your shot."
)

uploaded_file = st.file_uploader(
    "Upload a photo", type=["jpg", "jpeg", "png"], accept_multiple_files=False
)

if uploaded_file is not None:
    # Convert the uploaded file into an OpenCV image (BGR numpy array)
    pil_image = Image.open(uploaded_file).convert("RGB")
    rgb_array = np.array(pil_image)
    bgr_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)

    # Save to temp file for PhotoMentor processing
    temp_path = "temp_upload.jpg"
    cv2.imwrite(temp_path, bgr_array)

    mentor = PhotoMentor(temp_path)

    exp_grade, exp_advice, brightness = mentor.analyze_exposure()
    comp_grade, comp_advice, tilt = mentor.analyze_composition()
    sharp_grade, sharp_advice, sharpness = mentor.analyze_sharpness()
    sat_grade, sat_advice, saturation = mentor.analyze_saturation()

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Your Photo")
        st.image(pil_image, use_container_width=True)

        st.subheader("Composition Overlay")

        # Select guide overlay type dynamically
        guide_type = st.selectbox(
            "Select Guide Lines",
            (
                "Golden Spiral",
                "Rule of Thirds",
                "Golden Triangles",
                "Golden Ratio Grid",
                "Golden Section",
            ),
        )

        overlay_bgr = mentor.draw_composition_guide(guide_type=guide_type)
        overlay_rgb = cv2.cvtColor(overlay_bgr, cv2.COLOR_BGR2RGB)
        st.image(overlay_rgb, use_container_width=True)

    with col2:
        st.subheader("Diagnostic Report")

        def report_card(title, grade, advice, metric_label, metric_value):
            st.markdown(
                f"### {title} <span class='grade-badge'>{grade}</span>",
                unsafe_allow_html=True,
            )
            st.caption(f"{metric_label}: {metric_value:.1f}")
            st.write(advice)
            st.divider()

        report_card("Exposure", exp_grade, exp_advice, "Avg brightness (0-255)", brightness)
        report_card("Composition", comp_grade, comp_advice, "Tilt (degrees)", tilt)
        report_card("Sharpness", sharp_grade, sharp_advice, "Sharpness score", sharpness)
        report_card("Color Saturation", sat_grade, sat_advice, "Avg saturation (0-255)", saturation)

        # Master fixed photo section
        st.subheader("Master Fixed Photo")
        master_fixed_bgr = mentor.generate_master_fixed_image()
        master_fixed_rgb = cv2.cvtColor(master_fixed_bgr, cv2.COLOR_BGR2RGB)
        st.image(master_fixed_rgb, use_container_width=True)

else:
    st.info("Upload a JPG or PNG photo above to get started.")

st.markdown("---")
st.caption("Built with OpenCV + Streamlit · AI Photography Mentor project")
