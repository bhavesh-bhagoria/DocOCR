from flask import Flask, render_template, request, redirect, session
import cv2
import pytesseract
import os
import re
from db import create_tables, get_db
from auth import auth

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "secret-key"
app.register_blueprint(auth)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Create database tables
create_tables()

# -------------------------------------------------
# Helper functions
# -------------------------------------------------

def is_visually_blurry(image_path):
    """Detect visual blur using Laplacian variance."""
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    variance = cv2.Laplacian(image, cv2.CV_64F).var()
    return variance < 100


def extract_data(image_path):
    """Extract Name, DOB, Aadhaar from Aadhaar card."""

    image = cv2.imread(image_path)
    #image
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

    thresh = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

    text = pytesseract.image_to_string(thresh, config="--psm 6")
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    name = None
    dob = None
    aadhaar = None

    # -----------------------------
    # DOB + Name logic
    # -----------------------------
    dob_patterns = [
        r"\b\d{2}[/-]\d{2}[/-]\d{4}\b",
        r"\b\d{2}\s\d{2}\s\d{4}\b"
    ]

    dob_keywords = ["dob", "d.o.b", "date of birth"]

    for i, line in enumerate(lines):
        clean_line = line.lower().replace(".", "").replace(" ", "")

        if any(k.replace(".", "").replace(" ", "") in clean_line for k in dob_keywords):
            for pattern in dob_patterns:
                match = re.search(pattern, line)
                if match:
                    dob = match.group().replace("-", "/").replace(" ", "/")
                    break

            if i > 0:
                potential_name = lines[i - 1]
                noise = ["government", "india", "uidai", "aadhaar", "authority"]

                if (
                    len(potential_name) > 3
                    and not any(n in potential_name.lower() for n in noise)
                    and not re.search(r"\d", potential_name)
                ):
                    name = re.sub(r"[^A-Za-z\s]", "", potential_name).strip()
                    name = " ".join(name.split())
            break

    # -----------------------------
    # Aadhaar logic (reliable)
    # -----------------------------
    aadhaar_match = re.search(
        r"\b\d{4}\s?\d{4}\s?\d{4}\b|\b\d{12}\b",
        text
    )
    aadhaar = aadhaar_match.group() if aadhaar_match else None

    return name, dob, aadhaar


# -------------------------------------------------
# Routes
# -------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":
        files = request.files.getlist("files")

        conn = get_db()
        cursor = conn.cursor()

        for file in files:
            path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(path)

            # Step 1: Visual blur check (optional)
            visual_blur = is_visually_blurry(path)

            # Step 2: OCR extraction
            name, dob, aadhaar = extract_data(path)

            # Step 3: FINAL blur decision
            # Blur = YES if ANY field missing
            blur = not (name and dob and aadhaar)

            cursor.execute("""
                INSERT INTO documents (filename, is_blur, name, dob, aadhaar)
                VALUES (?, ?, ?, ?, ?)
            """, (file.filename, int(blur), name, dob, aadhaar))

        conn.commit()
        conn.close()

        return redirect("/results")

    return render_template("upload.html")


@app.route("/results")
def results():
    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    docs = conn.execute("SELECT * FROM documents").fetchall()
    conn.close()

    return render_template("results.html", docs=docs)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
