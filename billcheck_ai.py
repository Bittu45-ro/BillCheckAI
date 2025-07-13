import torch
from transformers import pipeline
from fpdf import FPDF
import base64
import streamlit as st
import fitz
import re
import pytesseract
from PIL import Image
import io

# Path to tesseract on Windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

st.set_page_config(page_title="BillCheck AI")
st.title("🧾 BillCheck AI - Smart AI for Smart Spending")

# Hugging Face API Key
hf_token = st.secrets["huggingface"]["api_key"]

# Load FLAN-T5 model
summarizer = pipeline("summarization", model="google/flan-t5-small", token=hf_token)

# PDF Text Extraction
def extract_text_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# Image Text Extraction
def extract_text_from_image(image_file):
    image = Image.open(image_file).convert("RGB")
    text = pytesseract.image_to_string(image)
    return text

# Summarize text
def generate_summary(text):
    chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
    summary = ""
    for chunk in chunks:
        output = summarizer(chunk, max_length=250, min_length=30, do_sample=False)
        summary += output[0]['summary_text'] + "\n\n"
    return summary

# Generate PDF from summary
def create_pdf(answer_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in answer_text.split('\n'):
        pdf.multi_cell(0, 10, line)
    pdf.output("billcheck_summary.pdf")
    with open("billcheck_summary.pdf", "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode("utf-8")
    return base64_pdf

# Detect fake tax rates
def detect_fake_tax_rates(text):
    valid_rates = ["0%", "5%", "12%", "18%", "28%"]
    found_rates = re.findall(r'\b\d{1,2}%\b', text)
    return [rate for rate in found_rates if rate not in valid_rates]

# Check GSTIN format
def check_gstin_validity(text):
    gstins = re.findall(r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b', text)
    return gstins if gstins else ["❌ No valid GSTIN found or possibly fake format."]

# --- Upload Section ---

st.subheader("📤 Upload a Bill (PDF or Image)")

pdf_file = st.file_uploader("Upload PDF Bill", type="pdf")
image_file = st.file_uploader("Or Upload Image Bill (JPG, PNG, HEIC/HEIF)", type=["jpg", "jpeg", "png", "heic", "heif"])

text = ""

if pdf_file:
    st.info("📖 Reading PDF...")
    text = extract_text_from_pdf(pdf_file)
    st.success("✅ PDF read successfully!")

elif image_file:
    st.info("🖼️ Extracting text from image...")
    try:
        text = extract_text_from_image(image_file)
        st.success("✅ Image text extracted!")
    except Exception as e:
        st.error("❌ Failed to read image. Make sure it's a valid format.")

# --- Process Text if Available ---

if text:
    st.markdown("---")
    st.subheader("🤖 AI Summary")
    summary = generate_summary(text)
    st.text_area("📄 AI Generated Summary", summary, height=300)

    st.markdown("---")
    st.subheader("🧪 GST & Tax Check")

    fake_taxes = detect_fake_tax_rates(text)
    if fake_taxes:
        st.warning(f"⚠️ Fake or unusual tax rates found: {', '.join(fake_taxes)}")
    else:
        st.success("✅ All tax rates look normal (0%, 5%, 12%, 18%, 28%).")

    gstins = check_gstin_validity(text)
    st.write("🔍 GSTIN Check:")
    for gstin in gstins:
        st.code(gstin)

    st.markdown("---")
    st.subheader("📥 Download Summary as PDF")
    base64_pdf = create_pdf(summary)
    download_link = f'<a href="data:application/pdf;base64,{base64_pdf}" download="BillCheck_AI_Summary.pdf">📄 Click to Download PDF</a>'
    st.markdown(download_link, unsafe_allow_html=True)