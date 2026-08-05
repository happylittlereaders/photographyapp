"""
streamlit_app.py
-----------------
Web UI for "Golden Number" photography evaluation app.
Features real-time camera viewfinder with mathematically accurate Golden Ratio overlays.
"""

import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import cv2
from PIL import Image

from photo_mentor import PhotoMentor

# Page Configuration
st.set_page_config(page_title="Golden Number", page_icon="✨", layout="wide")

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
    "Use the live interactive viewfinder to align your frame with precise composition guides in real-time, "
    "then capture or upload a photo for computer vision analysis and auto-corrections."
)

# ---------------------------------------------------------------------
# Helper: Precise Live Viewfinder Component (Golden Ratio Aspect Frame)
# ---------------------------------------------------------------------
def render_live_viewfinder(guide_type="Golden Spiral"):
    """Generates a responsive HTML5 video stream with accurate composition overlay guides."""
    
    if guide_type == "Rule of Thirds":
        svg_content = """
            <line x1="333.33" y1="0" x2="333.33" y2="618.03" stroke="#dcc86f" stroke-width="1" />
            <line x1="666.66" y1="0" x2="666.66" y2="618.03" stroke="#dcc86f" stroke-width="1" />
            <line x1="0" y1="206.01" x2="1000" y2="206.01" stroke="#dcc86f" stroke-width="1" />
            <line x1="0" y1="412.02" x2="1000" y2="412.02" stroke="#dcc86f" stroke-width="1" />
        """
    elif guide_type == "Golden Triangles":
        svg_content = """
            <line x1="0" y1="618.03" x2="1000" y2="0" stroke="#dcc86f" stroke-width="1" />
            <line x1="0" y1="0" x2="276.4" y2="447.2" stroke="#dcc86f" stroke-width="1" />
            <line x1="1000" y1="618.03" x2="723.6" y2="170.8" stroke="#dcc86f" stroke-width="1" />
        """
    elif guide_type == "Golden Section":
        svg_content = """
            <line x1="381.97" y1="0" x2="381.97" y2="618.03" stroke="#dcc86f" stroke-width="1" />
            <line x1="618.03" y1="0" x2="618.03" y2="618.03" stroke="#dcc86f" stroke-width="1" />
            <line x1="0" y1="236.07" x2="1000" y2="236.07" stroke="#dcc86f" stroke-width="1" />
            <line x1="0" y1="381.97" x2="1000" y2="381.97" stroke="#dcc86f" stroke-width="1" />
        """
    else:  # Default: Golden Spiral (True 1000x618.034 with Extended Inner Subsquares)
        svg_content = """
            <line x1="618.03" y1="0" x2="618.03" y2="618.03" stroke="#dcc86f" stroke-width="0.75" stroke-dasharray="3,3" opacity="0.45" />
            <line x1="618.03" y1="381.97" x2="1000" y2="381.97" stroke="#dcc86f" stroke-width="0.75" stroke-dasharray="3,3" opacity="0.45" />
            <line x1="763.93" y1="381.97" x2="763.93" y2="618.03" stroke="#dcc86f" stroke-width="0.75" stroke-dasharray="3,3" opacity="0.45" />
            <line x1="618.03" y1="472.14" x2="763.93" y2="472.14" stroke="#dcc86f" stroke-width="0.75" stroke-dasharray="3,3" opacity="0.45" />
            <line x1="708.20" y1="381.97" x2="708.20" y2="472.14" stroke="#dcc86f" stroke-width="0.75" stroke-dasharray="3,3" opacity="0.45" />
            <line x1="708.20" y1="437.69" x2="763.93" y2="437.69" stroke="#dcc86f" stroke-width="0.75" stroke-dasharray="3,3" opacity="0.45" />
            <line x1="729.49" y1="437.69" x2="729.49" y2="472.14" stroke="#dcc86f" stroke-width="0.75" stroke-dasharray="3,3" opacity="0.45" />
            <line x1="708.20" y1="450.85" x2="729.49" y2="450.85" stroke="#dcc86f" stroke-width="0.75" stroke-dasharray="3,3" opacity="0.45" />
            <line x1="721.36" y1="437.69" x2="721.36" y2="450.85" stroke="#dcc86f" stroke-width="0.75" stroke-dasharray="3,3" opacity="0.45" />

            <path d="
                M 0,618.03 
                A 618.03,618.03 0 0,1 618.03,0 
                A 381.97,381.97 0 0,1 1000,381.97 
                A 236.07,236.07 0 0,1 763.93,618.03 
                A 145.90,145.90 0 0,1 618.03,472.14 
                A 90.17,90.17 0 0,1 708.20,381.97 
                A 55.73,55.73 0 0,1 763.93,437.69 
                A 34.44,34.44 0 0,1 729.49,472.14 
                A 21.29,21.29 0 0,1 708.20,450.85
                A 13.16,13.16 0 0,1 721.36,437.69
                A 8.13,8.13 0 0,1 729.49,445.82
            " fill="none" stroke="#dcc86f" stroke-width="1.5" vector-effect="non-scaling-stroke" />
        """

    viewfinder_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{ box-sizing: border-box; }}
            body {{ margin: 0; padding: 0; background-color: #0f0f0f; font-family: sans-serif; overflow: hidden; }}
            .frame-wrapper {{
                position: relative;
                width: 100%;
                max-width: 560px;
                /* Locked to Golden Ratio Aspect (1.618 : 1) */
                aspect-ratio: 1.618 / 1;
                margin: 0 auto;
                border-radius: 8px;
                overflow: hidden;
                border: 1px solid #dcc86f;
            }}
            video {{
                width: 100%;
                height: 100%;
                object-fit: cover;
                display: block;
            }}
            svg {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: none;
            }}
            .badge {{
                position: absolute;
                top: 8px;
                left: 8px;
                background: rgba(15, 15, 15, 0.85);
                color: #dcc86f;
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 0.5px;
                border: 1px solid rgba(220, 200, 111, 0.5);
            }}
        </style>
    </head>
    <body>
        <div class="frame-wrapper">
            <video id="webcam" autoplay playsinline muted></video>
            <svg viewBox="0 0 1000 618.034" preserveAspectRatio="none">
                {svg_content}
            </svg>
            <div class="badge">LIVE GUIDE: {guide_type.upper()}</div>
        </div>

        <script>
            const video = document.getElementById('webcam');
            navigator.mediaDevices.getUserMedia({{ 
                video: {{ facingMode: {{ ideal: "environment" }}, width: {{ ideal: 1280 }}, height: {{ ideal: 720 }} }} 
            }})
            .then((stream) => {{ video.srcObject = stream; }})
            .catch((err) => {{ console.error("Camera access error:", err); }});
        </script>
    </body>
    </html>
    """
    components.html(viewfinder_html, height=380)

# ---------------------------------------------------------------------
# Input: Camera Capture OR File Upload
# ---------------------------------------------------------------------
input_tab, upload_tab = st.tabs(["📷 Take Photo", "🖼️ Upload Photo"])

captured_bytes = None

with input_tab:
    st.subheader("1. Real-Time Viewfinder & Capture")
    
    selected_live_guide = st.selectbox(
        "Select Composition Guide",
        ["Golden Spiral", "Rule of Thirds", "Golden Triangles", "Golden Section"],
        index=0
    )
    
    # Side-by-Side layout keeps the ratio guide visible alongside the camera control
    cam_col1, cam_col2 = st.columns([1, 1])
    
    with cam_col1:
        st.markdown("**Live Composition Guide**")
        render_live_viewfinder(guide_type=selected_live_guide)
        
    with cam_col2:
        st.markdown("**Snap Photo**")
        camera_file = st.camera_input("Take Picture", key="live_cam_input")
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

    # Section 2: Metric Breakdown & Adjustments
    st.divider()
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
    st.write("Below is the final clean image output combining all auto-corrections.")

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
