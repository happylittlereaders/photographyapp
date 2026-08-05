"""
streamlit_app.py
-----------------
Web UI for "Golden Number" photography evaluation app.
Displays initial image with toggleable ratio overlay, keeps final output clean.
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

# Custom Styling incorporating Hex #dcc86f prominently
st.markdown(
    """
    <style>
    :root {
        --primary-color: #dcc86f;
    }
    .main-title {
        color: #dcc86f;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 800;
        font-size: 2.8rem;
        margin-bottom: 0px;
        text-shadow: 0px 0px 14px rgba(220, 200, 111, 0.45);
    }
    .brand-accent-bar {
        height: 4px;
        width: 100%;
        background: linear-gradient(90deg, #dcc86f 0%, rgba(220, 200, 111, 0.1) 100%);
        border-radius: 2px;
        margin-top: 6px;
        margin-bottom: 22px;
    }
    .highlight-border {
        border-left: 4px solid #dcc86f;
        padding-left: 10px;
        margin-bottom: 20px;
    }
    /* Style active tabs and buttons with the theme color */
    button[role="tab"][aria-selected="true"] {
        border-bottom-color: #dcc86f !important;
        color: #dcc86f !important;
    }
    div.stButton > button:first-child {
        border-color: #dcc86f;
        color: #dcc86f;
        font-weight: 600;
    }
    div.stButton > button:first-child:hover {
        background-color: #dcc86f;
        color: #0f0f0f;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<h1 class='main-title'>✨ Golden Number</h1>", unsafe_allow_html=True)
st.markdown("<div class='brand-accent-bar'></div>", unsafe_allow_html=True)

st.write(
    "Take a photo or upload one to run computer vision diagnostic checks, preview artistic ratio guides "
    "(Golden Ratio, Triangles, Rule of Thirds), and auto-correct your shot."
)

# ---------------------------------------------------------------------
# Input: Camera capture OR File upload
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

    # Section 1: Photo Preview & Toggleable Ratio Overlay
    st.subheader("1. Composition & Ratio Preview")
    
    col_ctrl1, col_ctrl2 = st.columns([1, 2])
    with col_ctrl1:
        show_overlay = st.toggle("Overlay Composition Ratio", value=True)
    with col_ctrl2:
        selected_guide = st.selectbox(
            "Select Ratio Guide",
            ["Golden Spiral", "Rule of Thirds", "Golden Triangles", "Golden Section", "Golden Ratio Grid"],
            disabled=not show_overlay
        )

    p_col1, p_col2 = st.columns(2)

    with p_col1:
        st.image(pil_image, caption="Original Photo", use_container_width=True)

    with p_col2:
        if show_overlay:
            overlay_bgr = mentor.draw_composition_guide(guide_type=selected_guide)
            overlay_rgb = cv2.cvtColor(overlay_bgr, cv2.COLOR_BGR2RGB)
            st.image(overlay_rgb, caption=f"Ratio Overlay ({selected_guide})", use_container_width=True)
        else:
            st.image(pil_image, caption="Preview (Overlay Hidden)", use_container_width=True)

    st.divider()

    # Section 2: Metric Breakdown & Adjustments
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

    # Master Output Section (Clean Output - No Overlay)
    st.subheader("3. Master Corrected Result")
    st.write("Below is the final clean output combining all individual corrections.")

    master_fixed_bgr = mentor.generate_master_fixed_image()
    master_fixed_rgb = cv2.cvtColor(master_fixed_bgr, cv2.COLOR_BGR2RGB)

    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.image(pil_image, caption="Original Photo", use_container_width=True)
    with m_col2:
        st.image(master_fixed_rgb, caption="Final Corrected Image", use_container_width=True)

    # Download Button for Clean Final Image
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
