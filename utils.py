# utils.py
import pandas as pd
import PyPDF2
import pdfplumber
import os
from datetime import datetime, timedelta

# import Image
from tkinter import Image
import pytesseract
from datetime import datetime
import re


# Function to parse invoice data from PDF
# file_path = 'ABC Company - Invoice INV0001.pdf'
def read_invoice(file_path):
    """
    This method shall only accept PDF or Images of the invoice and we shall get the data out of it.
    """
    # file_extension = os.path.splitext(file_path)[1].lower()

    # if file_extension == ".pdf":
    # reading data from the pdf, handling pdf data
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"

    return text


def parse_invoice_metadata(text):
    """
    Parse through the data gathered by read_invoice()
    Returns metadata dictionary with corrected email assignments and due date handling
    """
    # Initialize a dictionary to store metadata
    metadata = {
        "invoice_number": None,
        "date": None,
        "due_date": None,
        "total_amount": None,
        "customer_name": None,
        "customer_email": None,
        "business_name": None,
        "business_email": None,
    }

    lines = text.split("\n")

    # Regex patterns for different fields
    invoice_pattern = re.compile(r"INV\d+")
    date_pattern = re.compile(r"\b\w{3,9} \d{1,2}, \d{4}\b")
    due_date_pattern = re.compile(r"due\b.*(?:\bon\b|\breceipt\b)", re.IGNORECASE)
    amount_pattern = re.compile(r"CAD \$\d+(\.\d{2})?")
    email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

    # First pass: Find business and customer sections
    bill_to_index = -1
    for i, line in enumerate(lines):
        if "BILL TO" in line:
            bill_to_index = i
            break

    # Extract values based on patterns
    for i, line in enumerate(lines):
        if not metadata["invoice_number"] and invoice_pattern.search(line):
            metadata["invoice_number"] = invoice_pattern.search(line).group()

        if not metadata["date"] and date_pattern.search(line):
            invoice_date = date_pattern.search(line).group()
            metadata["date"] = invoice_date
            # If no due date is found, set it to 30 days after invoice date
            if not metadata["due_date"]:
                try:
                    date_obj = datetime.strptime(invoice_date, "%b %d, %Y")
                    due_date = date_obj + timedelta(days=30)
                    metadata["due_date"] = due_date.strftime("%b %d, %Y")
                except ValueError:
                    metadata["due_date"] = "30 days from invoice date"

        if not metadata["due_date"] and due_date_pattern.search(line):
            metadata["due_date"] = line.strip()

        if not metadata["total_amount"] and amount_pattern.search(line):
            metadata["total_amount"] = amount_pattern.search(line).group()

        # Email handling with position-based logic
        if email_pattern.search(line):
            email = email_pattern.search(line).group()
            # If line is after BILL TO section, it's customer email
            if bill_to_index != -1 and i > bill_to_index:
                metadata["customer_email"] = email
            # If line is before BILL TO section, it's business email
            elif bill_to_index != -1 and i < bill_to_index:
                metadata["business_email"] = email

        # Match customer name based on 'BILL TO' line
        if i == bill_to_index + 1:  # Next line after "BILL TO"
            metadata["customer_name"] = line.strip()

        # Capture business name by looking for lines before "INVOICE"
        if "INVOICE" in line and i > 0:
            metadata["business_name"] = lines[i - 1].strip()

    return metadata


# Function to save and sort invoices by due date
def add_invoice(data, invoices):
    invoices.append(data)
    # Directly return the sorted list without assigning back to invoices
    return sorted(invoices, key=lambda x: x.get("due_date", "") or "")


# Initialize or load invoices
def load_invoices():
    # **Example**: Load from a CSV if it exists, otherwise return an empty list
    try:
        return pd.read_csv("invoices.csv").to_dict("records")
    except FileNotFoundError:
        return []
