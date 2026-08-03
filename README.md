# 📷 AI Photography Mentor

A web app that analyzes your photos and gives instant, plain-English feedback
on **exposure**, **composition**, **sharpness**, and **color** — like a
photography instructor reviewing your shot.

Built with Python, OpenCV, and Streamlit.

## Live Demo

_(Add your Streamlit Community Cloud link here once deployed, e.g._
`https://your-app-name.streamlit.app`_)_

## Features

- **Exposure analysis** — detects over/underexposed photos using brightness
  histograms and highlight-clipping detection
- **Composition analysis** — uses Canny edge detection + Hough Transform to
  detect a tilted horizon
- **Sharpness detection** — uses Laplacian variance to flag blurry photos
- **Color analysis** — checks HSV saturation for washed-out or oversaturated
  images
- **Rule-of-thirds overlay** — draws a composition guide grid on your photo

## Project Structure

```
.
├── streamlit_app.py     # Web UI (Streamlit)
├── photo_mentor.py       # Core image analysis logic (PhotoMentor class)
├── requirements.txt      # Python dependencies
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

Each analysis is a self-contained method on the `PhotoMentor` class in
`photo_mentor.py`:

| Check       | Technique                                   |
|-------------|----------------------------------------------|
| Exposure    | Grayscale histogram, average brightness      |
| Composition | Canny edges + Hough Line Transform, angle    |
| Sharpness   | Variance of the Laplacian                     |
| Color       | Average saturation in HSV color space         |

`streamlit_app.py` just handles the file upload, calls into `PhotoMentor`,
and displays the results.

## Roadmap / Ideas for Next Features

- [ ] Batch mode: upload/analyze a whole folder and export a PDF report
- [ ] Aesthetic scoring using a pretrained CNN (e.g. ResNet18 transfer
      learning) compared against a reference set of well-rated photos
- [ ] Downloadable annotated image (overlay + report as one image)
- [ ] Support for RAW file formats

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
