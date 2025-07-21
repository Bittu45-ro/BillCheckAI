import torch
from transformers import pipeline
from fpdf import FPDF
import base64
import streamlit as st
import fitz  # PyMuPDF
import re
import pytesseract
from PIL import Image
import platform

# ---------------- UI STYLES ----------------
st.markdown("""
    <style>
    html, body, [class*="css"]  {
        font-family: 'Segoe UI', sans-serif;
    }
    h1 {
        color: #0072E8;
        font-size: 40px;
    }
    .stTextArea textarea {
        background-color: #f9f9f9;
        border: 1px solid #ccc;
        border-radius: 8px;
        padding: 10px;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stButton > button {
        background-color: #0072E8;
        color: white;
        border: None;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton > button:hover {
        background-color: #005bb5;
        transform: scale(1.02);
    }
    a {
        color: #0072E8 !important;
        font-weight: bold;
    }
    hr {
        border-top: 1px solid #ccc;
        margin-top: 2rem;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------- STREAMLIT SETTINGS ----------------
st.set_page_config(page_title="BillCheck AI", layout="wide")

# ---------------- HEADER ----------------
col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.image("assets/logo.png", width=80)
with col_title:
    st.markdown("<h1 style='margin-bottom:0;'>🧾 <span style='color:#0072E8'>BillCheck AI</span></h1>", unsafe_allow_html=True)
    st.markdown("<p style='margin-top:0; color:gray;'>Smart AI for Smart Spending</p>", unsafe_allow_html=True)

# ---------------- LOAD SUMMARIZER ----------------
try:
    summarizer = pipeline("summarization", model="Falconsai/text_summarization")
except Exception as e:
    st.error(f"Error loading AI summarizer: {e}")
    summarizer = None

# ---------------- PLATFORM SETUP ----------------
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ---------------- TEXT EXTRACTION ----------------
def extract_text_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    return "\n".join([page.get_text() for page in doc])

def extract_text_from_image(image_file):
    try:
        image = Image.open(image_file).convert("RGB")
        return pytesseract.image_to_string(image)
    except Exception as e:
        st.error(f"Image processing failed: {e}")
        return ""

# ---------------- SUMMARIZATION ----------------
def generate_summary(text):
    if not summarizer:
        return "❌ Summarizer model could not be loaded."

    chunks = [text[i:i+400] for i in range(0, min(len(text), 1200), 400)]
    summary = ""
    for chunk in chunks:
        try:
            if len(chunk.strip()) < 30:
                continue
            output = summarizer(chunk, max_length=80, min_length=20, do_sample=False)
            summary += output[0]['summary_text'] + "\n\n"
        except Exception as e:
            summary += "[Error summarizing this part]\n\n"
            st.warning(f"⚠️ Summarization error: {e}")
    return summary.strip() or "No summary generated."

# ---------------- EXPORT TO PDF ----------------
def create_pdf(summary_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in summary_text.split('\n'):
        pdf.multi_cell(0, 10, line)
    pdf_file_path = "billcheck_summary.pdf"
    pdf.output(pdf_file_path)
    with open(pdf_file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# ---------------- VALIDATION CHECKS ----------------
def detect_fake_tax_rates(text):
    valid_rates = ["0%", "5%", "12%", "18%", "28%"]
    found_rates = re.findall(r'\b\d{1,2}%\b', text)
    return [rate for rate in found_rates if rate not in valid_rates]

def check_gstin_validity(text):
    gstins = re.findall(r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b', text)
    return gstins if gstins else ["❌ No valid GSTIN found or possibly fake format."]

# ---------------- MAIN APP ----------------
st.markdown("<hr style='border:1px solid #ddd;'>", unsafe_allow_html=True)
st.markdown("## 📤 Upload Your Bill")
st.caption("Supports PDF, JPG, PNG, HEIC formats")

col1, col2 = st.columns([1, 1])
text = ""

with col1:
    pdf_file = st.file_uploader("Upload PDF Bill", type=["pdf"])
with col2:
    image_file = st.file_uploader("Or Upload Image Bill", type=["jpg", "jpeg", "png", "heic", "heif"])

# Extract text
if pdf_file:
    st.info("📖 Reading PDF...")
    text = extract_text_from_pdf(pdf_file)
    st.success("✅ Text extracted from PDF!")

elif image_file:
    st.info("🖼️ Reading Image...")
    text = extract_text_from_image(image_file)
    if text:
        st.success("✅ Text extracted from Image!")

# Process the text
if text:
    st.markdown("<hr style='border:1px solid #ddd;'>", unsafe_allow_html=True)
    st.markdown("## 🤖 AI Generated Summary")

    if st.button("🔍 Generate AI Summary"):
        with st.spinner("Summarizing..."):
            summary = generate_summary(text)

        # Stylish card view
        st.markdown(f"""
            <div style="background-color:#f0f8ff;padding:15px 20px;border-left:5px solid #0072E8;border-radius:8px;">
                <h4>📄 AI Generated Summary:</h4>
                <p style="white-space:pre-wrap;">{summary}</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<hr style='border:1px solid #ddd;'>", unsafe_allow_html=True)
        st.markdown("## 🧪 GST & Tax Validation")

        fake_taxes = detect_fake_tax_rates(text)
        if fake_taxes:
            st.warning(f"⚠️ Unusual or fake tax rates found: {', '.join(fake_taxes)}")
        else:
            st.success("✅ All tax rates look valid (0%, 5%, 12%, 18%, 28%).")

        gstins = check_gstin_validity(text)
        st.markdown("🔍 **GSTIN Check:**")
        gstin_html = " ".join([f"<span style='background:#e3f2fd;padding:6px 10px;margin:4px;border-radius:6px;display:inline-block;font-weight:500;'>{g}</span>" for g in gstins])
        st.markdown(gstin_html, unsafe_allow_html=True)

        st.markdown("<hr style='border:1px solid #ddd;'>", unsafe_allow_html=True)
        st.markdown("## 📥 Download Your Bill Summary")

        base64_pdf = create_pdf(summary)
        download_link = f'<a href="data:application/pdf;base64,{base64_pdf}" download="BillCheck_AI_Summary.pdf">📄 Click to Download Summary PDF</a>'
        st.markdown(download_link, unsafe_allow_html=True)

# ---------------- FOOTER ----------------
st.markdown("""
    <hr style="border-top: 1px solid #ccc;">
    <div style='text-align: center; color: gray;'>
        BillCheck AI © 2025 | Built with ❤️ by Sai Hrithik
    </div>
""", unsafe_allow_html=True)
