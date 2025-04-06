from transformers import pipeline
from PyPDF2 import PdfReader
from reportlab.pdfgen import canvas
import os
import streamlit as st

redactor = pipeline("token-classification", model="iiiorg/piiranha-v1-detect-personal-information")

label_mapping = {
    "I-ACCOUNTNUM": "Account Number",
    "I-BUILDINGNUM": "Building Number",
    "I-CITY": "City",
    "I-CREDITCARDNUMBER": "Credit Card Number",
    "I-DATEOFBIRTH": "Date of Birth",
    "I-DRIVERLICENSENUM": "Driver License Number",
    "I-EMAIL": "Email",
    "I-GIVENNAME": "Given Name",
    "I-IDCARDNUM": "ID Card Number",
    "I-PASSWORD": "Password",
    "I-SOCIALNUM": "Social Security Number",
    "I-STREET": "Street",
    "I-SURNAME": "Surname",
    "I-TAXNUM": "Tax Number",
    "I-TELEPHONENUM": "Telephone Number",
    "I-USERNAME": "Username",
    "I-ZIPCODE": "Zip Code",
    "O": "Other"
}

def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def redact_and_group(text, selected_labels):
    detected_entities = redactor(text)

    detected_entities = sorted(detected_entities, key=lambda x: x['start'])

    redacted_spans = []
    current_span = None

    for entity in detected_entities:
        entity_start = entity['start']
        entity_end = entity['end']
        entity_label = entity.get('entity') 

        if selected_labels == "all" or label_mapping.get(entity_label, None) in selected_labels:
            if current_span is None:
                current_span = {'start': entity_start, 'end': entity_end}
            elif entity_start <= current_span['end']:
                current_span['end'] = max(current_span['end'], entity_end)
            else:
                redacted_spans.append(current_span)
                current_span = {'start': entity_start, 'end': entity_end}

    if current_span is not None:
        redacted_spans.append(current_span)

    redacted_text = text
    for span in reversed(redacted_spans): 
        redacted_text = redacted_text[:span['start']] + "*********" + redacted_text[span['end']:]

    return redacted_text

def create_redacted_pdf(redacted_text, output_path):
    c = canvas.Canvas(output_path)
    c.drawString(50, 800, "Redacted Document")  

    y_position = 780
    for line in redacted_text.split("\n"):
        c.drawString(50, y_position, line)
        y_position -= 12  

    c.save()

st.title("Automated Redaction")
st.write("Upload a PDF file to redact sensitive information.")

selected_labels = st.multiselect(
    "Select labels to redact",
    options=["all"] + list(label_mapping.values()),
    default=["all"]
)

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    temp_input_path = "temp_input.pdf"
    with open(temp_input_path, "wb") as f:
        f.write(uploaded_file.read())

    st.write("Extracting text from PDF...")
    extracted_text = extract_text_from_pdf(temp_input_path)

    st.text_area("Extracted Text", extracted_text, height=300)

    if st.button("Redact Text"):
        st.write("Redacting sensitive information...")
        redacted_text = redact_and_group(extracted_text, selected_labels)

        temp_output_path = "redacted_output.pdf"
        create_redacted_pdf(redacted_text, temp_output_path)

        with open(temp_output_path, "rb") as f:
            st.download_button(
                label="Download Redacted PDF",
                data=f,
                file_name="redacted_output.pdf",
                mime="application/pdf",
            )

        os.remove(temp_input_path)
        os.remove(temp_output_path)
