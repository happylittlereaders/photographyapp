"""
streamlit_app.py
-----------------
Web UI for "Golden Number" photography evaluation app.
Automatically applies ratio overlays on captured and processed photos.
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
        font-size: 2.6rem;
        margin-bottom: 0px;
        text-shadow: 0px 0px 12px rgba(220, 200, 111, 0.4);
    }
    .brand-accent-bar {
        height: 4px;
        width: 100%;
        background: linear-gradient(90deg, #dcc86f 0%, rgba(220, 200, 111, 0.1) 100%);
        border-radius: 2px;
        margin-top: 6px;
        margin-bottom: 18px;
    }
    .highlight-border {
        border-left: 4px solid #dcc86f;
        padding-left: 10px;
        margin-bottom: 20px;
    }
    div.stButton > button:first-child {
        border-color: #dcc86f;
        color: #dcc86f;
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
st.markdown("<div class='brand-accent-bar'></div>", unsafe_allow_html=True)

st.write(
    "Take a photo or upload one to run computer vision diagnostic checks, automatically overlay "
    "golden ratios and artistic guides, and preview auto-fixes."
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

    # Automatically generate Golden Spiral overlay by default
    default_overlay_bgr = mentor.draw_composition_guide(guide_type="Golden Spiral")
    default_overlay_rgb = cv2.cvtColor(default_overlay_bgr, cv2.COLOR_BGR2RGB)

    # Perform calculations
    exp_grade, exp_advice, brightness = mentor.analyze_exposure()
    comp_grade, comp_advice, tilt = mentor.analyze_composition()
    sharp_grade, sharp_advice, sharpness = mentor.analyze_sharpness()
    sat_grade, sat_advice, saturation = mentor.analyze_saturation()

    # Section 1: Image Capture + Automatic Overlay Display
    st.subheader("1. Photo Analysis with Golden Spiral Overlay")
    col1, col2 = st.columns([1, 1])

    with col1:
        st.image(pil_image, caption="Original Captured Photo", use_container_width=True)

    with col2:
        st.image(
            default_overlay_rgb, 
            caption="Automatic Ratio Overlay (Golden Spiral)", 
            use_container_width=True
        )

    # Optional selector if the user wants to switch ratio guides
    selected_guide = st.selectbox(
        "Switch Ratio Overlay Guide:",
        ["Golden Spiral", "Rule of Thirds", "Golden Triangles", "Golden Section", "Golden Ratio Grid"],
        index=0
    )
    
    if selected_guide != "Golden Spiral":
        custom_overlay_bgr = mentor.draw_composition_guide(guide_type=selected_guide)
        custom_overlay_rgb = cv2.cvtColor(custom_overlay_bgr, cv2.COLOR_BGR2RGB)
        st.image(custom_overlay_rgb, caption=f"Active Guide: {selected_guide}", use_container_width=True)

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

    # Master Output Section
    st.subheader("3. Master Corrected Result")
    st.write("Below is the final output combining all individual corrections with the composition overlay applied.")

    master_fixed_bgr = mentor.generate_master_fixed_image()
    
    # Automatically apply overlay to final output image
    master_mentor = PhotoMentor(temp_path)
    master_mentor.img = master_fixed_bgr
    master_fixed_overlay_bgr = master_mentor.draw_composition_guide(guide_type=selected_guide)
    master_fixed_overlay_rgb = cv2.cvtColor(master_fixed_overlay_bgr, cv2.COLOR_BGR2RGB)

    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.image(pil_image, caption="Original Photo", use_container_width=True)
    with m_col2:
        st.image(master_fixed_overlay_rgb, caption="Final Corrected Image (with Overlay)", use_container_width=True)

    # Download Button
    success, encoded_img = cv2.imencode(".jpg", master_fixed_overlay_bgr)
    if success:
        st.download_button(
            label="⬇️ Download corrected photo with overlay",
            data=encoded_img.tobytes(),
            file_name="golden_number_corrected.jpg",
            mime="image/jpeg",
        )

else:
    st.info("Take a photo or upload a JPG/PNG above to analyze and auto-correct.")
