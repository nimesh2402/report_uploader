import streamlit as st
import pandas as pd
import requests
import io
import anthropic
import PyPDF2
import time
import csv
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, storage, firestore

import json

if not firebase_admin._apps:
    cred_dict = json.loads(st.secrets["firebase"]["credentials"])
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred, {
        'storageBucket': st.secrets["firebase"]["storage_bucket"]
    })

# Set up Anthropic client
client = anthropic.Anthropic(api_key=st.secrets["anthropic"]["api_key"])

# Set up Firebase clients
bucket = storage.bucket()
db = firestore.client()

SYSTEM_PROMPT = """
You are an expert medical data analyst. Your task is to extract relevant test results from medical reports and format them into a CSV structure.

Key points:
- Extract all relevant test results from the provided text.
- Format the date as DD-MM-YYYY.
- Use the following headers when applicable: FBS, PP2BS, HBA1C, S. CREAT, S. POTASSIUM, TG, LDL, TSH, UACR, VITAMIN D, SGPT, AMH, LH, FSH, DHEAS, 17-OHP, PROLACTIN, TESTOSTERONE, S. CORTISOL, S. SODIUM, FREE T4, IGF1, S. CALCIUM, S. PHOSPHORUS, ALP, PTH, FREE T3, HB, WBC, URINE PUS.
- If a test doesn't match these headers, use an appropriate ALL CAPS header.
- Ensure all headers are in ALL CAPS.
- The CSV should have the following columns: Date, Test Name, Test Value, Test Unit, Normal Range.
- Do not include any explanatory text or summaries, only the CSV data.
"""

def claude_request(prompt, system=SYSTEM_PROMPT):
    try:
        st.text("Sending request to Claude...")
        start_time = time.time()
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=4000,
            temperature=0,
            system=system,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        end_time = time.time()
        st.text(f"Claude request completed in {end_time - start_time:.2f} seconds")
        return message.content[0].text
    except Exception as e:
        st.error(f"An error occurred while calling Claude: {str(e)}")
        return None

def extract_text_from_pdf(pdf_file):
    st.text("Extracting text from PDF...")
    start_time = time.time()
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    end_time = time.time()
    st.text(f"PDF text extraction completed in {end_time - start_time:.2f} seconds")
    return text

def process_report(report_text):
    st.text("Processing report...")
    prompt = f"""
    Extract all relevant test results from the following medical report and format them into a CSV structure:\n\n{report_text}

    **OUTPUT INSTRUCTIONS**

    1. The CSV file will have no heading
    2. The CSV file should have 4 columns only which are as follows:
    Date,Test Name,Test Value,Test Comment
    3. The Test name should be preferably be adapted to the following test name:
    FBS, PP2BS, HBA1C, S. CREAT, S. POTASSIUM, TG, LDL, TSH, UACR, VITAMIN D, SGPT, AMH, LH, FSH, DHEAS, 17-OHP, PROLACTIN, TESTOSTERONE, S. CORTISOL, S. SODIUM, FREE T4, IGF1, S. CALCIUM, S. PHOSPHORUS, ALP, PTH, FREE T3
    4. The test name cannot be adapted to the above name, then retain the name but give it in all caps 
    5. In the test comments section add the Unit and the normal range and the interpretation comments (Normal etc)

    **IMPORTANT INSTRUCTIONS**
    If there are no text or reports extracted from the uploaded file, Please don't make up or hallucinate reports. Just give the output as : Data could not be extracted because of some reason
    """

    csv_output = claude_request(prompt)
    return csv_output

def upload_to_firebase(patient_name, file, csv_data):
    st.text("Uploading to Firebase...")
    try:
        # Upload PDF to Firebase Storage
        file_name = f"{patient_name}_{file.name}"
        blob = bucket.blob(file_name)
        blob.upload_from_file(file)

        # Save patient details and CSV data to Firestore
        doc_ref = db.collection('patients').document(patient_name)
        doc_ref.set({
            'name': patient_name,
            'upload_date': datetime.now(),
            'file_name': file_name,
            'csv_data': csv_data
        })

        st.success(f"Uploaded {file_name} to Firebase successfully!")
    except Exception as e:
        st.error(f"Error uploading to Firebase: {str(e)}")

def main():
    st.title("Dr. Om J Lakhani Report Uploader")

    # Input fields
    patient_name = st.text_input("Name of the patient")
    date_time = datetime.now().strftime("%d-%m-%Y")
    phone_number = st.text_input("Contact number")
    email = st.text_input("Email address")

    # File uploader
    uploaded_files = st.file_uploader("Upload PDF of Reports. Multiple files can be uploaded", type=["pdf"],
                                      accept_multiple_files=True)

    if st.button("Submit"):
        if uploaded_files and patient_name and date_time and phone_number and email:
            st.success(
                "Thank you for uploading the report. Please keep the window open for a few seconds to allow us to process the data")

            # Process reports and upload to Firebase
            for file in uploaded_files:
                report_text = extract_text_from_pdf(file)
                csv_output = process_report(report_text)
                upload_to_firebase(patient_name, file, csv_output)

            st.success("All files processed and uploaded successfully!")

        else:
            st.warning("Please fill in all fields and upload at least one file.")

if __name__ == "__main__":
    main()
