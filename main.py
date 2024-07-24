import streamlit as st
import firebase_admin
from firebase_admin import credentials, storage, firestore
import json
from datetime import datetime

# Initialize Firebase
if not firebase_admin._apps:
    # Parse the credentials JSON string into a dictionary
    cred_dict = json.loads(st.secrets["firebase"]["credentials"])
    
    # Create a credential object from the dictionary
    cred = credentials.Certificate(cred_dict)
    
    firebase_admin.initialize_app(cred, {
        'storageBucket': st.secrets["firebase"]["storage_bucket"]
    })

# Get Firebase services
db = firestore.client()
bucket = storage.bucket()

def upload_to_firebase(patient_name, contact_number, email, file):
    st.text("Uploading to Firebase...")
    try:
        # Reset the file pointer to the beginning
        file.seek(0)
        
        # Upload PDF to Firebase Storage
        file_name = f"{patient_name}_{file.name}"
        blob = bucket.blob(file_name)
        blob.upload_from_file(file)

        # Save patient details to Firestore
        doc_ref = db.collection('patients').document(patient_name)
        doc_ref.set({
            'name': patient_name,
            'contact_number': contact_number,
            'email': email,
            'upload_date': datetime.now(),
            'file_name': file_name
        })

        st.success(f"Uploaded {file_name} to Firebase successfully!")
    except Exception as e:
        st.error(f"Error uploading to Firebase: {str(e)}")

def main():
    st.title("Dr. Om J Lakhani Report Uploader")

    # Input fields
    patient_name = st.text_input("Name of the patient")
    contact_number = st.text_input("Contact number")
    email = st.text_input("Email address")

    # File uploader
    uploaded_file = st.file_uploader("Upload PDF of Report", type=["pdf"])

    if st.button("Submit"):
        if uploaded_file and patient_name and contact_number and email:
            upload_to_firebase(patient_name, contact_number, email, uploaded_file)
        else:
            st.warning("Please fill in all fields and upload a file.")

if __name__ == "__main__":
    main()
