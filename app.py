import streamlit as st
import os
import pandas as pd
from utils import read_invoice, add_invoice, load_invoices, parse_invoice_metadata
from datetime import datetime

# Page configuration
st.set_page_config(page_title="Invoice Manager", layout="wide")

# Heading
st.title("Invoice Upload and Management")

# Initialize invoice storage
if "invoices" not in st.session_state:
    st.session_state.invoices = load_invoices()

# File upload
st.subheader("Upload Invoice (PDF format)")
uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file:
    # Parse the uploaded invoice
    invoice_data = read_invoice(uploaded_file)
    metadata = parse_invoice_metadata(invoice_data)

    # Ensure due_date is in a sortable format (if not already)
    if metadata["due_date"] and "On Receipt" not in metadata["due_date"]:
        try:
            metadata["due_date"] = datetime.strptime(
                metadata["due_date"], "%b %d, %Y"
            ).strftime("%Y-%m-%d")
        except ValueError:
            st.warning(
                "Due date format not recognized. Assuming today as due date for sorting purposes."
            )
            metadata["due_date"] = datetime.today().strftime("%Y-%m-%d")

    # Update the session state with new invoice data
    st.session_state.invoices = add_invoice(metadata, st.session_state.invoices)
    st.success("Invoice uploaded and parsed successfully!")

# Display uploaded invoices sorted by Due Date
st.subheader("Uploaded Invoices Sorted by Due Date")
if st.session_state.invoices:
    invoice_df = pd.DataFrame(st.session_state.invoices)
    # Ensure due_date column is of datetime type for proper sorting
    invoice_df["due_date"] = pd.to_datetime(invoice_df["due_date"], errors="coerce")
    invoice_df_sorted = invoice_df.sort_values(by="due_date").reset_index(drop=True)
    st.dataframe(invoice_df_sorted)
else:
    st.info("No invoices uploaded yet.")

# **Optional**: Button to save invoices to a CSV file
if st.session_state.invoices:

    @st.cache_data
    def convert_df(df):
        return df.to_csv(index=False).encode("utf-8")

    csv = convert_df(pd.DataFrame(st.session_state.invoices))

    st.download_button(
        label="Download Invoices as CSV",
        data=csv,
        file_name="invoices.csv",
        mime="text/csv",
    )
