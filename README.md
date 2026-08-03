# 🔱 Golden Number

A web app that overlays classic composition guides on your photos — Rule of
Thirds, Golden Ratio Grid, Golden Triangle, and Golden Spiral — diagnoses
exposure, sharpness, and color issues, and auto-corrects each one with a
before/after comparison, finishing with one fully touched-up image.

## Live Demo

_(Add your Streamlit Community Cloud link here once deployed, e.g._
`https://your-app-name.streamlit.app`_)_

## Features

- **Composition guides** — Rule of Thirds, Golden Ratio Grid, Golden
  Triangle (selectable diagonal direction), and Golden Spiral, overlaid
  directly on your photo
- **Exposure analysis** — detects over/underexposed photos using brightness
  histograms and highlight-clipping detection
- **Composition analysis** — uses Canny edge detection + Hough Transform to
  detect a tilted horizon
- **Sharpness detection** — uses Laplacian variance to flag blurry photos
- **Color analysis** — checks HSV saturation for washed-out or oversaturated
  images
- **Auto-fix with before/after comparison** — for every flaw that's
  detected (exposure, tilt, blur, saturation), see the corrected version
  side by side with the original
- **Final enhanced image** — every needed correction combined into one
  downloadable photo

## Project Structure

```
.
├── streamlit_app.py       # Web UI (Streamlit)
├── photo_mentor.py         # Core image analysis, guides, and fixes (PhotoMentor class)
├── requirements.txt        # Python dependencies
├── .streamlit/
│   └── config.toml         # Theme (brand color #dcc86f)
├── .gitignore
└── README.md
```

## Running Locally

1. Clone the repo:
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   cd YOUR_REPO_NAME
   ```

2. (Recommended) create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate      # on Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the app:
   ```bash
   streamlit run streamlit_app.py
   ```

5. It will open in your browser at `http://localhost:8501`.

## Deploying for Free (Streamlit Community Cloud)

1. Push this repo to GitHub (public or private).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app**, select this repo and branch, and set the main file
   path to `streamlit_app.py`.
4. Click **Deploy**. You'll get a public URL you can share or add to a
   portfolio/application.

## How It Works

Each analysis, guide overlay, and fix is a self-contained method on the
`PhotoMentor` class in `photo_mentor.py`:

| Check       | Technique                                   |
|-------------|------------------------------------------------|
| Exposure    | Grayscale histogram, average brightness, highlight clipping |
| Composition | Canny edges + Hough Line Transform, tilt angle |
| Sharpness   | Variance of the Laplacian                     |
| Color       | Average saturation in HSV color space         |

| Guide              | How it's drawn                                        |
|---------------------|--------------------------------------------------------|
| Rule of Thirds       | Grid lines at 1/3 and 2/3 of width/height              |
| Golden Ratio Grid    | Grid lines at 38.2% / 61.8% of width/height             |
| Golden Triangle      | A corner-to-corner diagonal plus perpendiculars dropped from the other two corners |
| Golden Spiral        | Recursive square-cutting (Fibonacci) with quarter-circle arcs |

| Fix         | How it's corrected                                     |
|-------------|-----------------------------------------------------------|
| Exposure    | CLAHE contrast correction + brightness shift toward a mid-gray target |
| Composition | Rotates the image by the measured tilt angle to level the horizon |
| Sharpness   | Unsharp masking (weighted blend against a Gaussian blur) |
| Saturation  | Scales the HSV saturation channel toward a natural target |

`streamlit_app.py` handles the file upload, lets you pick which guides to
overlay, calls into `PhotoMentor` for diagnostics and fixes, shows
before/after comparisons for anything flagged, and combines every needed
fix into one final downloadable image.

## Roadmap / Ideas for Next Features

- [ ] Batch mode: upload/analyze a whole folder and export a PDF report
- [ ] Aesthetic scoring using a pretrained CNN (e.g. ResNet18 transfer
      learning) compared against a reference set of well-rated photos
- [ ] Support for RAW file formats
- [ ] Adjustable correction strength (sliders instead of fixed targets)

## License

This project does not currently include a license file. If you plan to make
the repo public, consider adding one (e.g. MIT) so others know how they can
use the code — see [choosealicense.com](https://choosealicense.com/) for a
quick guide to picking one.

## Notes on Data

If you later train an aesthetic-scoring model, be mindful of the licensing
of any photos you use as training/reference data (e.g. competition winners,
scraped images). Public datasets like AVA (Aesthetic Visual Analysis) exist
specifically for this kind of research use — prefer those over scraping
photos you don't have rights to.
