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

if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Streamlit Page Settings
st.set_page_config(page_title="BillCheck AI")
st.title("🧾 BillCheck AI - Smart AI for Smart Spending")

# Hugging Face API Key (stored securely in Streamlit Secrets)
hf_token = st.secrets["huggingface"]["api_key"]

# Load the summarization pipeline
# Use a smaller model and correct token param
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6", token=hf_token)

# --- TEXT EXTRACTION FUNCTIONS ---

def extract_text_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_text_from_image(image_file):
    try:
        image = Image.open(image_file).convert("RGB")
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        st.error(f"Image processing failed: {e}")
        return ""

# --- SUMMARY GENERATION ---

def generate_summary(text):
    chunks = [text[i:i+400] for i in range(0, len(text), 400)]
    summary = ""
    for chunk in chunks:
        try:
            if len(chunk.strip()) < 30:
                continue  # Skip too short text chunks
            output = summarizer(chunk, max_length=80, min_length=20, do_sample=False)
            summary += output[0]['summary_text'] + "\n\n"
        except Exception as e:
            summary += "[Error summarizing this part]\n\n"
            st.warning(f"⚠️ Summarization error: {e}")
    return summary or "No summary generated."

# --- PDF EXPORT ---

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

# --- CHECK FUNCTIONS ---

def detect_fake_tax_rates(text):
    valid_rates = ["0%", "5%", "12%", "18%", "28%"]
    found_rates = re.findall(r'\b\d{1,2}%\b', text)
    return [rate for rate in found_rates if rate not in valid_rates]

def check_gstin_validity(text):
    gstins = re.findall(r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b', text)
    return gstins if gstins else ["❌ No valid GSTIN found or possibly fake format."]

# --- UI SECTION ---

st.subheader("📤 Upload a Bill (PDF or Image)")

pdf_file = st.file_uploader("Upload PDF Bill", type=["pdf"])
image_file = st.file_uploader("Or Upload Image Bill (JPG, PNG, HEIC/HEIF)", type=["jpg", "jpeg", "png", "heic", "heif"])

text = ""

# Read input
if pdf_file:
    st.info("📖 Reading PDF...")
    text = extract_text_from_pdf(pdf_file)
    st.success("✅ Text extracted from PDF!")

elif image_file:
    st.info("🖼️ Reading Image...")
    try:
        text = extract_text_from_image(image_file)
        st.success("✅ Text extracted from Image!")
    except Exception as e:
        st.error("❌ Failed to extract text from image.")

# Process if text exists
if text:
    st.markdown("---")
    st.subheader("🤖 AI Summary")
    summary = generate_summary(text)
    st.text_area("📄 AI Generated Summary", summary, height=300)

    st.markdown("---")
    st.subheader("🧪 GST & Tax Check")

    fake_taxes = detect_fake_tax_rates(text)
    if fake_taxes:
        st.warning(f"⚠️ Unusual or fake tax rates found: {', '.join(fake_taxes)}")
    else:
        st.success("✅ All tax rates look valid (0%, 5%, 12%, 18%, 28%).")

    gstins = check_gstin_validity(text)
    st.write("🔍 GSTIN Check:")
    for gstin in gstins:
        st.code(gstin)

    st.markdown("---")
    st.subheader("📥 Download Summary as PDF")
    base64_pdf = create_pdf(summary)
    download_link = f'<a href="data:application/pdf;base64,{base64_pdf}" download="BillCheck_AI_Summary.pdf">📄 Click to Download Summary PDF</a>'
    st.markdown(download_link, unsafe_allow_html=True)
