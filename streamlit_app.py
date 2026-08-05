"""
streamlit_app.py
-----------------
Web UI for "Golden Number" photography evaluation app.
Supports camera capture, active ratio overlay selections, and brand hex display.
"""

import streamlit as st
import numpy as np
import cv2
from PIL import Image

from photo_mentor import PhotoMentor

# Page Configuration
st.set_page_config(page_title="Golden Number", page_icon="✨", layout="wide")

# PWA support
st.markdown(
    """
    <link rel="manifest" href="/app/static/manifest.json">
    <meta name="theme-color" content="#dcc86f">
    """,
    unsafe_allow_html=True,
)

# Custom Styling incorporating Hex #dcc86f
st.markdown(
    """
    <style>
    :root {
        --primary-color: #dcc86f;
    }
    .main-title {
        color: #dcc86f;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        margin-bottom: 0px;
    }
    .hex-badge {
        background-color: #dcc86f;
        color: #0f0f0f;
        font-weight: 800;
        padding: 6px 14px;
        border-radius: 20px;
        display: inline-block;
        font-size: 0.9rem;
        letter-spacing: 1px;
        margin-bottom: 15px;
        box-shadow: 0 2px 5px rgba(220, 200, 111, 0.3);
    }
    .highlight-border {
        border-left: 4px solid #dcc86f;
        padding-left: 10px;
        margin-bottom: 20px;
    }
    div.stButton > button:first-child {
        border-color: #dcc86f;
    }
    button[role="tab"] {
        font-size: 1rem;
        padding: 0.6rem 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<h1 class='main-title'>✨ Golden Number</h1>", unsafe_allow_html=True)

# Prominent Hex Display
st.markdown("<div class='hex-badge'>THEME HEX: #DCC86F</div>", unsafe_allow_html=True)

st.write(
    "Take a photo or upload one to run computer vision diagnostic checks, explore artistic guides "
    "(Golden Ratio, Triangles, Rule of Thirds), and preview step-by-step auto-fixes."
)

# Sidebar / Top-Level Composition Overlay Selector
st.sidebar.title("📐 Live Overlay Settings")
enable_live_overlay = st.sidebar.checkbox("Overlay ratio guide on input photo", value=True)
selected_guide = st.sidebar.selectbox(
    "Select Composition Ratio Guide",
    ["Golden Spiral", "Rule of Thirds", "Golden Triangles", "Golden Section", "Golden Ratio Grid"],
    index=0
)

# ---------------------------------------------------------------------
# Input: camera capture OR file upload
# ---------------------------------------------------------------------
input_tab, upload_tab = st.tabs(["📷 Take Photo", "🖼️ Upload Photo"])

captured_bytes = None

with input_tab:
    camera_file = st.camera_input("Take a picture")
    if camera_file is not None:
        captured_bytes = camera_file

with upload_tab:
    uploaded_file = st.file_uploader(
        "Upload a photo", type=["jpg", "jpeg", "png"], accept_multiple_files=False
    )
    if uploaded_file is not None:
        captured_bytes = uploaded_file

if captured_bytes is not None:
    # Convert upload/capture to BGR numpy array
    pil_image = Image.open(captured_bytes).convert("RGB")
    rgb_array = np.array(pil_image)
    bgr_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)

    temp_path = "temp_upload.jpg"
    cv2.imwrite(temp_path, bgr_array)

    mentor = PhotoMentor(temp_path)

    # Perform calculations
    exp_grade, exp_advice, brightness = mentor.analyze_exposure()
    comp_grade, comp_advice, tilt = mentor.analyze_composition()
    sharp_grade, sharp_advice, sharpness = mentor.analyze_sharpness()
    sat_grade, sat_advice, saturation = mentor.analyze_saturation()

    # Top Section: Original vs Overlay Preview
    st.subheader("1. Composition Overlay Guides")
    col1, col2 = st.columns([1, 1])

    with col1:
        st.image(pil_image, caption="Original Photo", use_container_width=True)

    with col2:
        if enable_live_overlay:
            overlay_bgr = mentor.draw_composition_guide(guide_type=selected_guide)
            overlay_rgb = cv2.cvtColor(overlay_bgr, cv2.COLOR_BGR2RGB)
            st.image(overlay_rgb, caption=f"Photo with Overlay: {selected_guide}", use_container_width=True)
        else:
            st.image(pil_image, caption="Overlay Disabled", use_container_width=True)

    st.divider()

    # Diagnostic & Interactive Step-by-Step Fixes
    st.subheader("2. Metric Breakdown & Before/After Adjustments")

    def display_metric_section(title, grade, advice, metric_label, metric_value, is_imperfect, fix_func):
        st.markdown(f"### {title}: **{grade}**")
        st.caption(f"{metric_label}: {metric_value:.1f}")
        st.write(advice)

        if is_imperfect:
            st.warning(f"Correction suggested for {title.lower()}.")
            fixed_bgr = fix_func()
            fixed_rgb = cv2.cvtColor(fixed_bgr, cv2.COLOR_BGR2RGB)

            comp_col1, comp_col2 = st.columns(2)
            with comp_col1:
                st.image(pil_image, caption="Before", use_container_width=True)
            with comp_col2:
                st.image(fixed_rgb, caption=f"After ({title} Adjusted)", use_container_width=True)
        else:
            st.success(f"{title} is optimal! No adjustments needed.")

        st.divider()

    # Exposure Section
    exp_imperfect = exp_grade != "Well exposed"
    display_metric_section(
        "Exposure", exp_grade, exp_advice, "Avg brightness (0-255)", brightness, exp_imperfect, mentor.fix_exposure
    )

    # Composition (Tilt) Section
    comp_imperfect = comp_grade == "Tilted"
    display_metric_section(
        "Composition (Level)", comp_grade, comp_advice, "Tilt (degrees)", tilt, comp_imperfect, mentor.fix_composition
    )

    # Sharpness Section
    sharp_imperfect = sharp_grade == "Possibly blurry"
    display_metric_section(
        "Sharpness", sharp_grade, sharp_advice, "Sharpness score", sharpness, sharp_imperfect, mentor.fix_sharpness
    )

    # Saturation Section
    sat_imperfect = sat_grade != "Natural"
    display_metric_section(
        "Color Saturation", sat_grade, sat_advice, "Avg saturation (0-255)", saturation, sat_imperfect, mentor.fix_saturation
    )

    # Master Output Section
    st.subheader("3. Master Corrected Result")
    st.write("Below is the final output combining all individual corrections (Exposure, Leveling, Sharpening, Saturation Balancing).")

    master_fixed_bgr = mentor.generate_master_fixed_image()
    master_fixed_rgb = cv2.cvtColor(master_fixed_bgr, cv2.COLOR_BGR2RGB)

    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.image(pil_image, caption="Original Photo", use_container_width=True)
    with m_col2:
        st.image(master_fixed_rgb, caption="Final Corrected Image", use_container_width=True)

    # Download Button
    success, encoded_img = cv2.imencode(".jpg", master_fixed_bgr)
    if success:
        st.download_button(
            label="⬇️ Download corrected photo",
            data=encoded_img.tobytes(),
            file_name="golden_number_corrected.jpg",
            mime="image/jpeg",
        )

else:
    st.info("Take a photo or upload a JPG/PNG above to analyze and auto-correct.")
