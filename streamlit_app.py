"""
streamlit_app.py
-----------------
Web UI for "Golden Number" photography evaluation app.
Features real-time camera viewfinders, photographer dataset presets, automatic style transfers,
expanded Golden Spiral sub-squares, pop-ups with 2 attributed sample images per composition guide,
draggable leading lines, editable adjustment sliders, colorblind-friendly output, and an
attention/contrast heatmap.
"""

import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import cv2
from PIL import Image

import base64
import io

try:
    # streamlit-drawable-canvas-fix is the maintained fork of the original
    # (now-archived) streamlit-drawable-canvas package; it keeps the same
    # `streamlit_drawable_canvas` import path so this is a drop-in swap.
    from streamlit_drawable_canvas import st_canvas
    CANVAS_AVAILABLE = True

    # The canvas's background image normally goes through Streamlit's
    # image_to_url helper, which for non-tiny images serves it from
    # Streamlit's MediaFileManager as a separate URL the browser fetches
    # after the component mounts. That fetch can race the media manager
    # registering the file — especially inside conditional blocks (like
    # ours, gated on an uploaded photo) or on Streamlit Cloud — and the
    # canvas renders solid black when it loses that race. Forcing every
    # background image to inline as a base64 data URI instead removes the
    # extra network round-trip entirely, so there's nothing to race.
    try:
        import streamlit.elements.image as _st_image_module

        def _inline_data_uri(image, *_args, **_kwargs):
            if not isinstance(image, Image.Image):
                image = Image.fromarray(image)
            buf = io.BytesIO()
            image.convert("RGB").save(buf, format="PNG")
            encoded = base64.b64encode(buf.getvalue()).decode()
            return f"data:image/png;base64,{encoded}"

        _st_image_module.image_to_url = _inline_data_uri
    except Exception:
        pass
except ImportError:
    CANVAS_AVAILABLE = False

# Import module and force reload to avoid cached import errors
import photo_mentor
import importlib
importlib.reload(photo_mentor)
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
    "Select a legendary photographer profile or use the default dataset. "
    "Align your composition using real-time dynamic overlays, then analyze and auto-correct your image into that photographer's signature style!"
)

# ---------------------------------------------------------------------
# Shared Golden Spiral SVG builder
# ---------------------------------------------------------------------
def build_golden_spiral_svg_content(vb_w, vb_h, stroke_width=1.5, dash=None, opacity=0.85, color="#dcc86f"):
    """
    Builds SVG markup for the golden spiral overlay (nested sub-squares +
    connecting spiral arc) using the shared geometry engine in PhotoMentor,
    so the "Explain Guide" popup and the live viewfinder always render the
    exact same, correct spiral.
    """
    geometry = PhotoMentor.golden_spiral_svg_geometry(vb_w, vb_h)
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""

    parts = []
    for (sx, sy, sw, sh) in geometry["squares"]:
        parts.append(
            f'<rect x="{sx:.2f}" y="{sy:.2f}" width="{sw:.2f}" height="{sh:.2f}" '
            f'fill="none" stroke="{color}" stroke-width="{stroke_width}"{dash_attr} opacity="{opacity}" />'
        )
    parts.append(
        f'<path d="{geometry["path"]}" fill="none" stroke="{color}" '
        f'stroke-width="{stroke_width * 1.8:.2f}" vector-effect="non-scaling-stroke" opacity="{min(1.0, opacity + 0.1)}" />'
    )
    return "\n".join(parts)


# ---------------------------------------------------------------------
# Composition Guide Information & 2 Attributed Sample Images Dictionary
# ---------------------------------------------------------------------
GUIDE_EXPLANATIONS = {
    "Golden Spiral": {
        "title": "🌀 Golden Spiral (Fibonacci Spiral)",
        "explanation": (
            "The Golden Spiral uses nested Fibonacci sub-squares based on the Golden Ratio (1:1.618). "
            "It guides the viewer's eye along a fluid, sweeping curve directly into the smallest sub-squares at the focal origin."
        ),
        "viewbox": "0 0 1000 618.034",
        "aspect_ratio": "1.618 / 1",
        "samples": [
            {
                "img_url": "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?w=800&auto=format&fit=crop",
                "page_url": "https://unsplash.com/photos/ES2-KaB4RNo",
                "caption": "1. Curved Forest Path — The natural curve leads from the foreground directly to the focal light.",
                "citation": "Photo by Luca Bravo via Unsplash"
            },
            {
                "img_url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&auto=format&fit=crop",
                "page_url": "https://unsplash.com/photos/KMn4VEeE21U",
                "caption": "2. Seashore Waves — The sweeping shoreline curve echoes the logarithmic arc into the horizon.",
                "citation": "Photo by Sean Oulashin via Unsplash"
            }
        ]
    },
    "Rule of Thirds": {
        "title": "📐 Rule of Thirds",
        "explanation": (
            "Divides the frame into a 3x3 grid with two vertical and two horizontal lines. "
            "Primary elements are placed along the grid lines or directly at their four intersecting power points."
        ),
        "viewbox": "0 0 900 600",
        "aspect_ratio": "3 / 2",
        "samples": [
            {
                "img_url": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&auto=format&fit=crop",
                "page_url": "https://unsplash.com/photos/NR_S2369wbU",
                "caption": "1. Valley Horizon — Horizon line placed precisely along the lower horizontal third line.",
                "citation": "Photo by Bailey Zindel via Unsplash"
            },
            {
                "img_url": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&auto=format&fit=crop",
                "page_url": "https://unsplash.com/photos/sp-p7uuT0tw",
                "caption": "2. Forest Tree Trunk — Vertical subject positioned along the right vertical grid line.",
                "citation": "Photo by Sebastian Unrau via Unsplash"
            }
        ]
    },
    "Golden Triangles": {
        "title": "🔺 Golden Triangles",
        "explanation": (
            "Divides the frame using a main diagonal line and two perpendicular bisecting lines to form golden right triangles. "
            "Creates dynamic leading lines and strong diagonal momentum across the scene."
        ),
        "viewbox": "0 0 900 600",
        "aspect_ratio": "3 / 2",
        "samples": [
            {
                "img_url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=800&auto=format&fit=crop",
                "page_url": "https://unsplash.com/photos/dW2_L80Xn4U",
                "caption": "1. Skyscraper Diagonals — Sharp architectural lines align along the main diagonal bisector.",
                "citation": "Photo by Sean Pollock via Unsplash"
            },
            {
                "img_url": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=800&auto=format&fit=crop",
                "page_url": "https://unsplash.com/photos/m_X961xW3mI",
                "caption": "2. Sand Dunes — Rolling desert ridges cut cleanly across the diagonal triangle lines.",
                "citation": "Photo by Keith Hardy via Unsplash"
            }
        ]
    },
    "Golden Section": {
        "title": "✨ Golden Section (Phi Grid)",
        "explanation": (
            "Uses the precise Golden Ratio (1:0.618:1) to generate a tighter central column and row. "
            "Provides a more harmonic, subtle placement than standard thirds, ideal for fine-art compositions."
        ),
        "viewbox": "0 0 900 600",
        "aspect_ratio": "3 / 2",
        "samples": [
            {
                "img_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&auto=format&fit=crop",
                "page_url": "https://unsplash.com/photos/d1UPi8S6-4I",
                "caption": "1. Fine Art Portrait — Subject's eyes align perfectly with the upper Phi grid intersection.",
                "citation": "Photo by Atyani Muhammad via Unsplash"
            },
            {
                "img_url": "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=800&auto=format&fit=crop",
                "page_url": "https://unsplash.com/photos/ww3_92kW912",
                "caption": "2. Architectural Interior — Central room structure frames neatly within the 0.618 golden center row.",
                "citation": "Photo by Samantha Brooks via Unsplash"
            }
        ]
    }
}

# ---------------------------------------------------------------------
# Pop-Up Dialog Modal Function (2 Attributed Images Layout)
# ---------------------------------------------------------------------
@st.dialog("Composition Guide Breakdown & Examples", width="large")
def show_guide_dialog(guide_name):
    info = GUIDE_EXPLANATIONS.get(guide_name, GUIDE_EXPLANATIONS["Golden Spiral"])
    st.subheader(info["title"])
    st.write(info["explanation"])
    st.markdown("---")

    vb_parts = [float(val) for val in info["viewbox"].split()]
    vb_w, vb_h = vb_parts[2], vb_parts[3]

    # SVG Overlay Definition
    if guide_name == "Rule of Thirds":
        svg_overlay = f"""
            <line x1="{vb_w * 0.333}" y1="0" x2="{vb_w * 0.333}" y2="{vb_h}" stroke="#dcc86f" stroke-width="3" />
            <line x1="{vb_w * 0.666}" y1="0" x2="{vb_w * 0.666}" y2="{vb_h}" stroke="#dcc86f" stroke-width="3" />
            <line x1="0" y1="{vb_h * 0.333}" x2="{vb_w}" y2="{vb_h * 0.333}" stroke="#dcc86f" stroke-width="3" />
            <line x1="0" y1="{vb_h * 0.666}" x2="{vb_w}" y2="{vb_h * 0.666}" stroke="#dcc86f" stroke-width="3" />
            <circle cx="{vb_w * 0.333}" cy="{vb_h * 0.333}" r="8" fill="#dcc86f" />
            <circle cx="{vb_w * 0.666}" cy="{vb_h * 0.333}" r="8" fill="#dcc86f" />
            <circle cx="{vb_w * 0.333}" cy="{vb_h * 0.666}" r="8" fill="#dcc86f" />
            <circle cx="{vb_w * 0.666}" cy="{vb_h * 0.666}" r="8" fill="#dcc86f" />
        """
    elif guide_name == "Golden Triangles":
        svg_overlay = f"""
            <line x1="0" y1="{vb_h}" x2="{vb_w}" y2="0" stroke="#dcc86f" stroke-width="3" />
            <line x1="0" y1="0" x2="{vb_w * 0.276}" y2="{vb_h * 0.723}" stroke="#dcc86f" stroke-width="3" />
            <line x1="{vb_w}" y1="{vb_h}" x2="{vb_w * 0.723}" y2="{vb_h * 0.276}" stroke="#dcc86f" stroke-width="3" />
            <circle cx="{vb_w * 0.276}" cy="{vb_h * 0.723}" r="8" fill="#dcc86f" />
            <circle cx="{vb_w * 0.723}" cy="{vb_h * 0.276}" r="8" fill="#dcc86f" />
        """
    elif guide_name == "Golden Section":
        svg_overlay = f"""
            <line x1="{vb_w * 0.382}" y1="0" x2="{vb_w * 0.382}" y2="{vb_h}" stroke="#dcc86f" stroke-width="3" />
            <line x1="{vb_w * 0.618}" y1="0" x2="{vb_w * 0.618}" y2="{vb_h}" stroke="#dcc86f" stroke-width="3" />
            <line x1="0" y1="{vb_h * 0.382}" x2="{vb_w}" y2="{vb_h * 0.382}" stroke="#dcc86f" stroke-width="3" />
            <line x1="0" y1="{vb_h * 0.618}" x2="{vb_w}" y2="{vb_h * 0.618}" stroke="#dcc86f" stroke-width="3" />
            <circle cx="{vb_w * 0.382}" cy="{vb_h * 0.382}" r="8" fill="#dcc86f" />
            <circle cx="{vb_w * 0.618}" cy="{vb_h * 0.382}" r="8" fill="#dcc86f" />
            <circle cx="{vb_w * 0.382}" cy="{vb_h * 0.618}" r="8" fill="#dcc86f" />
            <circle cx="{vb_w * 0.618}" cy="{vb_h * 0.618}" r="8" fill="#dcc86f" />
        """
    else:  # Golden Spiral / Golden Ratio — built from the shared, geometrically
        # correct generator instead of hard-coded coordinates, so it always shows.
        svg_overlay = build_golden_spiral_svg_content(vb_w, vb_h, stroke_width=2, opacity=0.9)

    # Side-by-side layout for 2 images
    col1, col2 = st.columns(2)
    samples = info["samples"]

    for idx, col in enumerate([col1, col2]):
        sample = samples[idx]
        with col:
            st.markdown(
                f"""
                <div style="width:100%; border: 1.5px solid #dcc86f; border-radius: 8px; position: relative; aspect-ratio: {info['aspect_ratio']}; overflow: hidden; background: #1a1a1a;">
                    <img src="{sample['img_url']}" style="width: 100%; height: 100%; object-fit: cover; display: block; filter: brightness(0.85);" />
                    <svg viewBox="{info['viewbox']}" preserveAspectRatio="none" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;">
                        {svg_overlay}
                    </svg>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(f"**{sample['caption']}**")
            st.markdown(f"[{sample['citation']}]({sample['page_url']})")

    st.write("")
    if st.button("Close Guide", use_container_width=True):
        st.rerun()

# ---------------------------------------------------------------------
# Photographer Presets Configuration
# ---------------------------------------------------------------------
PHOTOGRAPHER_PRESETS = {
    "Default (Golden Ratio)": {
        "aspect_ratio": "1.618 / 1",
        "viewbox": "0 0 1000 618.034",
        "default_guide": "Golden Spiral",
        "description": "Standard golden ratio framing (1.618:1) with balanced, realistic post-processing.",
        "style_config": {
            "contrast_factor": 1.05,
            "saturation_factor": 1.1,
            "monochrome": False,
            "grain": False,
            "vignette": False,
            "warmth": 0.0
        }
    },
    "Dorothea Lange": {
        "aspect_ratio": "4 / 3",
        "viewbox": "0 0 1000 750",
        "default_guide": "Rule of Thirds",
        "description": "Humanist documentary pioneer (4:3 ratio). Deep B&W tonal gradation, lifted shadow detail, and storytelling focus.",
        "style_config": {
            "contrast_factor": 1.2,
            "saturation_factor": 0.0,
            "monochrome": True,
            "grain": True,
            "vignette": True,
            "warmth": 0.0
        }
    },
    "Vivian Maier": {
        "aspect_ratio": "1 / 1",
        "viewbox": "0 0 800 800",
        "default_guide": "Golden Section",
        "description": "Iconic street portraitist (1:1 medium format Rolleiflex ratio). Punchy black & white with medium film grain.",
        "style_config": {
            "contrast_factor": 1.3,
            "saturation_factor": 0.0,
            "monochrome": True,
            "grain": True,
            "vignette": False,
            "warmth": 0.0
        }
    },
    "Annie Leibovitz": {
        "aspect_ratio": "3 / 2",
        "viewbox": "0 0 900 600",
        "default_guide": "Golden Section",
        "description": "Dramatic editorial portraiture (3:2 ratio). Cinematic contrast, rich cool shadows, and high color depth.",
        "style_config": {
            "contrast_factor": 1.35,
            "saturation_factor": 1.25,
            "monochrome": False,
            "grain": False,
            "vignette": True,
            "cool_shadows": True,
            "warmth": 0.0
        }
    },
    "Henri Cartier-Bresson": {
        "aspect_ratio": "3 / 2",
        "viewbox": "0 0 900 600",
        "default_guide": "Golden Triangles",
        "description": "Street photography pioneer (3:2 Leica ratio). High-contrast, candid monochrome with geometric precision.",
        "style_config": {
            "contrast_factor": 1.35,
            "saturation_factor": 0.0,
            "monochrome": True,
            "grain": True,
            "vignette": False,
            "warmth": 0.0
        }
    },
    "Ansel Adams": {
        "aspect_ratio": "5 / 4",
        "viewbox": "0 0 1000 800",
        "default_guide": "Rule of Thirds",
        "description": "Large-format landscape master (5:4 view camera ratio). Deep Zone System blacks, crisp highlights, and vignetting.",
        "style_config": {
            "contrast_factor": 1.50,
            "saturation_factor": 0.0,
            "monochrome": True,
            "grain": False,
            "vignette": True,
            "warmth": 0.0
        }
    },
    "Steve McCurry": {
        "aspect_ratio": "3 / 2",
        "viewbox": "0 0 900 600",
        "default_guide": "Golden Section",
        "description": "Vibrant narrative photojournalism (3:2 ratio). Rich saturation, deep warm tones, and strong subject emphasis.",
        "style_config": {
            "contrast_factor": 1.25,
            "saturation_factor": 1.45,
            "monochrome": False,
            "grain": False,
            "vignette": True,
            "warmth": 1.2
        }
    }
}

# Select Preset
selected_preset_name = st.selectbox(
    "📸 Choose Photographer Style / Dataset",
    list(PHOTOGRAPHER_PRESETS.keys()),
    index=0
)

active_preset = PHOTOGRAPHER_PRESETS[selected_preset_name]
st.info(f"**Style Note:** {active_preset['description']}")

# ---------------------------------------------------------------------
# Helper: Precise Dynamic Viewfinder Component
# ---------------------------------------------------------------------
def render_live_viewfinder(guide_type="Golden Spiral", aspect_ratio="1.618 / 1", viewbox="0 0 1000 618.034"):
    vb_parts = [float(val) for val in viewbox.split()]
    vb_w, vb_h = vb_parts[2], vb_parts[3]

    if guide_type == "Rule of Thirds":
        svg_content = f"""
            <line x1="{vb_w * 0.333}" y1="0" x2="{vb_w * 0.333}" y2="{vb_h}" stroke="#dcc86f" stroke-width="1" />
            <line x1="{vb_w * 0.666}" y1="0" x2="{vb_w * 0.666}" y2="{vb_h}" stroke="#dcc86f" stroke-width="1" />
            <line x1="0" y1="{vb_h * 0.333}" x2="{vb_w}" y2="{vb_h * 0.333}" stroke="#dcc86f" stroke-width="1" />
            <line x1="0" y1="{vb_h * 0.666}" x2="{vb_w}" y2="{vb_h * 0.666}" stroke="#dcc86f" stroke-width="1" />
        """
    elif guide_type == "Golden Triangles":
        svg_content = f"""
            <line x1="0" y1="{vb_h}" x2="{vb_w}" y2="0" stroke="#dcc86f" stroke-width="1" />
            <line x1="0" y1="0" x2="{vb_w * 0.276}" y2="{vb_h * 0.723}" stroke="#dcc86f" stroke-width="1" />
            <line x1="{vb_w}" y1="{vb_h}" x2="{vb_w * 0.723}" y2="{vb_h * 0.276}" stroke="#dcc86f" stroke-width="1" />
        """
    elif guide_type == "Golden Section":
        svg_content = f"""
            <line x1="{vb_w * 0.382}" y1="0" x2="{vb_w * 0.382}" y2="{vb_h}" stroke="#dcc86f" stroke-width="1" />
            <line x1="{vb_w * 0.618}" y1="0" x2="{vb_w * 0.618}" y2="{vb_h}" stroke="#dcc86f" stroke-width="1" />
            <line x1="0" y1="{vb_h * 0.382}" x2="{vb_w}" y2="{vb_h * 0.382}" stroke="#dcc86f" stroke-width="1" />
            <line x1="0" y1="{vb_h * 0.618}" x2="{vb_w}" y2="{vb_h * 0.618}" stroke="#dcc86f" stroke-width="1" />
        """
    else:  # Golden Spiral / Golden Ratio — shared, geometrically correct generator.
        svg_content = build_golden_spiral_svg_content(
            vb_w, vb_h, stroke_width=0.75, dash="3,3", opacity=0.45, color="#dcc86f"
        )

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
                max-width: 500px;
                aspect-ratio: {aspect_ratio};
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
            <svg viewBox="{viewbox}" preserveAspectRatio="none">
                {svg_content}
            </svg>
            <div class="badge">PRESET: {selected_preset_name.upper()} ({guide_type.upper()})</div>
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
    components.html(viewfinder_html, height=420)

# ---------------------------------------------------------------------
# Input: Camera Capture OR File Upload
# ---------------------------------------------------------------------
input_tab, upload_tab = st.tabs(["📷 Take Photo", "🖼️ Upload Photo"])

captured_bytes = None

default_guide_idx = ["Golden Spiral", "Rule of Thirds", "Golden Triangles", "Golden Section"].index(
    active_preset.get("default_guide", "Golden Spiral")
)

with input_tab:
    st.subheader("1. Real-Time Viewfinder & Capture")

    col_guide_sel, col_guide_btn = st.columns([3, 1])
    with col_guide_sel:
        selected_live_guide = st.selectbox(
            "Select Composition Guide",
            ["Golden Spiral", "Rule of Thirds", "Golden Triangles", "Golden Section"],
            index=default_guide_idx,
            key="guide_select_box"
        )
    with col_guide_btn:
        st.write("")
        st.write("")
        if st.button("ℹ️ Explain Guide", use_container_width=True):
            show_guide_dialog(selected_live_guide)

    cam_col1, cam_col2 = st.columns([1, 1])

    with cam_col1:
        st.markdown("**Live Composition Guide**")
        render_live_viewfinder(
            guide_type=selected_live_guide,
            aspect_ratio=active_preset["aspect_ratio"],
            viewbox=active_preset["viewbox"]
        )

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
    pil_image = Image.open(captured_bytes).convert("RGB")
    rgb_array = np.array(pil_image)
    bgr_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)

    temp_path = "temp_upload.jpg"
    cv2.imwrite(temp_path, bgr_array)

    mentor = PhotoMentor(temp_path, target_aspect_ratio_str=active_preset["aspect_ratio"])

    cropped_rgb = cv2.cvtColor(mentor.img, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(cropped_rgb)

    exp_grade, exp_advice, brightness = mentor.analyze_exposure()
    comp_grade, comp_advice, tilt = mentor.analyze_composition()
    sharp_grade, sharp_advice, sharpness = mentor.analyze_sharpness()
    sat_grade, sat_advice, saturation = mentor.analyze_saturation()

    # -------------------------------------------------------------
    # 2. Fine-Tune Adjustments (editable sliders + revert button)
    # -------------------------------------------------------------
    st.divider()
    st.subheader("2. Fine-Tune Adjustments")
    st.caption(
        f"These start at the recommended values for **{selected_preset_name}**. "
        "Drag any slider to override them, or revert back at any time."
    )

    # Reset sliders to the new preset's recommended values whenever the
    # preset itself changes (not on every rerun).
    if st.session_state.get("_active_preset_for_sliders") != selected_preset_name:
        st.session_state["_active_preset_for_sliders"] = selected_preset_name
        defaults = active_preset["style_config"]
        st.session_state["user_contrast_factor"] = defaults.get("contrast_factor", 1.0)
        st.session_state["user_saturation_factor"] = defaults.get("saturation_factor", 1.0)
        st.session_state["user_warmth"] = defaults.get("warmth", 0.0)
        st.session_state["user_monochrome"] = defaults.get("monochrome", False)
        st.session_state["user_grain"] = defaults.get("grain", False)
        st.session_state["user_vignette"] = defaults.get("vignette", False)

    preview_col, slider_col = st.columns([1, 1])

    with slider_col:
        revert_row, _ = st.columns([2, 1])
        with revert_row:
            if st.button("↺ Revert to Recommended", use_container_width=True):
                defaults = active_preset["style_config"]
                st.session_state["user_contrast_factor"] = defaults.get("contrast_factor", 1.0)
                st.session_state["user_saturation_factor"] = defaults.get("saturation_factor", 1.0)
                st.session_state["user_warmth"] = defaults.get("warmth", 0.0)
                st.session_state["user_monochrome"] = defaults.get("monochrome", False)
                st.session_state["user_grain"] = defaults.get("grain", False)
                st.session_state["user_vignette"] = defaults.get("vignette", False)
                st.rerun()

        user_contrast = st.slider("Contrast", 0.5, 2.0, step=0.05, key="user_contrast_factor")
        user_saturation = st.slider("Saturation", 0.0, 2.0, step=0.05, key="user_saturation_factor")
        user_warmth = st.slider("Warmth (cool ↔ warm)", -2.0, 2.0, step=0.1, key="user_warmth")
        cb1, cb2, cb3 = st.columns(3)
        with cb1:
            user_monochrome = st.checkbox("Monochrome", key="user_monochrome")
        with cb2:
            user_grain = st.checkbox("Film grain", key="user_grain")
        with cb3:
            user_vignette = st.checkbox("Vignette", key="user_vignette")

    user_style_config = {
        "contrast_factor": user_contrast,
        "saturation_factor": user_saturation,
        "warmth": user_warmth,
        "monochrome": user_monochrome,
        "grain": user_grain,
        "vignette": user_vignette,
        "cool_shadows": active_preset["style_config"].get("cool_shadows", False),
    }

    with preview_col:
        st.markdown("**Live Preview**")
        st.caption("Updates as you move the sliders (composition & leading lines are applied later).")
        preview_master = mentor.generate_master_fixed_image(user_style_config)
        preview_styled = mentor.apply_photographer_style(preview_master, user_style_config)
        preview_rgb = cv2.cvtColor(preview_styled, cv2.COLOR_BGR2RGB)
        st.image(preview_rgb, use_container_width=True)

    st.divider()
    st.subheader(f"3. Metric Breakdown & {selected_preset_name} Tailored Fixes")

    def display_metric_section(title, grade, advice, metric_label, metric_value, is_imperfect, fix_func):
        st.markdown(f"### {title}: **{grade}**")
        st.caption(f"{metric_label}: {metric_value:.1f}")
        st.write(advice)

        if is_imperfect or user_style_config.get("monochrome", False):
            st.warning(f"Adjustment applied matching {selected_preset_name} profile.")

            if title in ["Exposure", "Sharpness", "Color Saturation"]:
                fixed_bgr = fix_func(style_config=user_style_config)
            else:
                fixed_bgr = fix_func()

            fixed_rgb = cv2.cvtColor(fixed_bgr, cv2.COLOR_BGR2RGB)

            comp_col1, comp_col2 = st.columns(2)
            with comp_col1:
                st.image(pil_image, caption=f"Conformed Input ({active_preset['aspect_ratio']})", use_container_width=True)
            with comp_col2:
                st.image(fixed_rgb, caption=f"After ({title} Adjusted for {selected_preset_name})", use_container_width=True)
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

    # -------------------------------------------------------------
    # 4. Add Leading Lines (draw + drag on the photo)
    # -------------------------------------------------------------
    st.subheader("4. Add Leading Lines")

    lines_overlay_rgba = None

    if not CANVAS_AVAILABLE:
        st.warning(
            "Leading-line drawing needs the `streamlit-drawable-canvas-fix` package. "
            "Add it to requirements.txt and reinstall to enable this section."
        )
    else:
        st.caption(
            "Draw a line by clicking-and-dragging across the photo. Switch to "
            "'Move / edit lines' to drag an existing line into place."
        )

        line_mode = st.radio(
            "Mode", ["Draw new line", "Move / edit lines"], horizontal=True, key="leading_line_mode"
        )
        drawing_mode = {"Draw new line": "line", "Move / edit lines": "transform"}[line_mode]

        lc1, lc2 = st.columns(2)
        with lc1:
            line_color = st.color_picker("Leading line color", "#dcc86f", key="leading_line_color")
        with lc2:
            line_width = st.slider("Line thickness", 1, 12, 3, key="leading_line_width")

        # The component's own built-in undo/redo/clear toolbar renders inside
        # its iframe with dark icons on a dark background and can't be
        # restyled from here, so it's turned off in favor of native,
        # brand-colored Streamlit buttons backed by a small history stack.
        if "canvas_key_version" not in st.session_state:
            st.session_state["canvas_key_version"] = 0
        if "canvas_snapshots" not in st.session_state:
            st.session_state["canvas_snapshots"] = []

        undo_col, clear_col, _ = st.columns([1, 1, 2])
        with undo_col:
            if st.button(
                "↺ Undo last line", use_container_width=True,
                disabled=not st.session_state["canvas_snapshots"],
            ):
                st.session_state["canvas_snapshots"].pop()
                st.session_state["canvas_key_version"] += 1
                st.rerun()
        with clear_col:
            if st.button(
                "🗑️ Clear all lines", use_container_width=True,
                disabled=not st.session_state["canvas_snapshots"],
            ):
                st.session_state["canvas_snapshots"] = []
                st.session_state["canvas_key_version"] += 1
                st.rerun()

        max_canvas_w = 700
        scale = min(1.0, max_canvas_w / pil_image.width)
        canvas_w = max(1, int(pil_image.width * scale))
        canvas_h = max(1, int(pil_image.height * scale))
        canvas_bg = pil_image.resize((canvas_w, canvas_h), Image.LANCZOS)

        initial_drawing = st.session_state["canvas_snapshots"][-1] if st.session_state["canvas_snapshots"] else None
        canvas_key = f"leading_lines_canvas_{st.session_state['canvas_key_version']}"

        canvas_result = st_canvas(
            fill_color="rgba(0,0,0,0)",
            stroke_width=line_width,
            stroke_color=line_color,
            background_image=canvas_bg,
            height=canvas_h,
            width=canvas_w,
            drawing_mode=drawing_mode,
            initial_drawing=initial_drawing,
            display_toolbar=False,
            key=canvas_key,
        )

        # Track a snapshot each time a new line is added, so "Undo" has
        # something to roll back to.
        if canvas_result.json_data is not None:
            objects = canvas_result.json_data.get("objects", [])
            snapshots = st.session_state["canvas_snapshots"]
            prev_len = len(snapshots[-1].get("objects", [])) if snapshots else 0
            if len(objects) > prev_len:
                snapshots.append(canvas_result.json_data)

        if canvas_result.image_data is not None and np.any(canvas_result.image_data[:, :, 3] > 0):
            lines_overlay_rgba = Image.fromarray(
                canvas_result.image_data.astype("uint8"), "RGBA"
            ).resize(pil_image.size)

            base_rgba = pil_image.convert("RGBA")
            combined = Image.alpha_composite(base_rgba, lines_overlay_rgba).convert("RGB")
            st.image(combined, caption="Photo with leading lines", use_container_width=True)


    st.divider()

    # -------------------------------------------------------------
    # 5. Master Result: style, accessibility, and heatmap
    # -------------------------------------------------------------
    st.subheader(f"5. Master Result: {selected_preset_name} Style")
    st.write(f"Combines general technical corrections with color grading tailored to **{selected_preset_name}**.")

    acc_col1, acc_col2 = st.columns(2)
    with acc_col1:
        cb_enabled = st.checkbox("🎨 Colorblind-friendly mode", value=False)
        cb_type_key = "deuteranopia"
        if cb_enabled:
            cb_choice = st.selectbox(
                "Optimize for",
                [
                    "Deuteranopia — red-green (most common)",
                    "Protanopia — red-green",
                    "Tritanopia — blue-yellow",
                ],
            )
            cb_type_key = {
                "Deuteranopia — red-green (most common)": "deuteranopia",
                "Protanopia — red-green": "protanopia",
                "Tritanopia — blue-yellow": "tritanopia",
            }[cb_choice]
    with acc_col2:
        show_heatmap = st.checkbox("🔥 Show attention / contrast heatmap", value=False)

    master_fixed_bgr = mentor.generate_master_fixed_image(user_style_config)
    styled_bgr = mentor.apply_photographer_style(master_fixed_bgr, user_style_config)

    # Bake in any leading lines the user drew.
    if lines_overlay_rgba is not None:
        styled_rgba = cv2.cvtColor(styled_bgr, cv2.COLOR_BGR2RGBA)
        styled_pil = Image.fromarray(styled_rgba, "RGBA")
        styled_pil = Image.alpha_composite(styled_pil, lines_overlay_rgba)
        styled_bgr = cv2.cvtColor(np.array(styled_pil.convert("RGB")), cv2.COLOR_RGB2BGR)

    if cb_enabled:
        styled_bgr = mentor.apply_colorblind_correction(styled_bgr, cb_type=cb_type_key)

    styled_rgb = cv2.cvtColor(styled_bgr, cv2.COLOR_BGR2RGB)

    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.image(pil_image, caption=f"Original Conformed Image ({active_preset['aspect_ratio']})", use_container_width=True)
    with m_col2:
        st.image(styled_rgb, caption=f"Final Output ({selected_preset_name} Preset)", use_container_width=True)

    if show_heatmap:
        heatmap_overlay, _ = mentor.generate_attention_heatmap(styled_bgr)
        heatmap_rgb = cv2.cvtColor(heatmap_overlay, cv2.COLOR_BGR2RGB)
        st.image(
            heatmap_rgb,
            caption="Attention heatmap — brighter areas are most likely to catch the eye",
            use_container_width=True,
        )

    success, encoded_img = cv2.imencode(".jpg", styled_bgr)
    if success:
        st.download_button(
            label=f"⬇️ Download {selected_preset_name} styled photo",
            data=encoded_img.tobytes(),
            file_name=f"golden_number_{selected_preset_name.lower().replace(' ', '_')}.jpg",
            mime="image/jpeg",
        )

else:
    st.info("Take a photo or upload a JPG/PNG above to analyze and auto-correct.")
