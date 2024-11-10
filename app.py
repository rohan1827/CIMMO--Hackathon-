import streamlit as st
import os
import pandas as pd
from utils import read_invoice, add_invoice, load_invoices, parse_invoice_metadata
from datetime import datetime
import streamlit.components.v1 as components


def create_interactive_table(invoices_data):
    """Create an interactive HTML table with sorting capabilities"""

    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(invoices_data)

    # Calculate payment differences
    df["prev_amount"] = df.groupby("business_name")["total_amount"].shift(1)
    df["amount_difference"] = df.apply(
        lambda x: calculate_amount_difference(x["total_amount"], x["prev_amount"]),
        axis=1,
    )

    # Create HTML content
    html_content = """
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <style>
        .invoice-table {
            width: 100%;
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 0.9em;
            font-family: sans-serif;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
            background-color: white;
        }
        .invoice-table thead tr {
            background-color: #009879;
            color: #ffffff;
            text-align: left;
        }
        .invoice-table th,
        .invoice-table td {
            padding: 12px 15px;
            color: #333333;
        }
        .invoice-table tbody tr {
            border-bottom: 1px solid #dddddd;
        }
        .invoice-table tbody tr:nth-of-type(even) {
            background-color: #f3f3f3;
        }
        .invoice-table tbody tr:last-of-type {
            border-bottom: 2px solid #009879;
        }
        .sort-btn {
            background: none;
            border: none;
            color: white;
            cursor: pointer;
            padding: 5px;
        }
        .sort-btn:hover {
            text-decoration: underline;
        }
        .higher-amount {
            color: red;
            font-weight: bold;
        }
        .normal-amount {
            color: #333333;
        }
        .send-reminder {
            background-color: #4CAF50;
            color: white;
            padding: 5px 10px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 5px;
        }
        .send-reminder:hover {
            background-color: #45a049;
        }
        .pay-button {
            background-color: #007bff;
            color: white;
            padding: 5px 10px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .pay-button:hover {
            background-color: #0056b3;
        }
        .action-buttons {
            display: flex;
            gap: 5px;
        }
    </style>
    
    <table class="invoice-table" id="invoiceTable">
        <thead>
            <tr>
                <th><button class="sort-btn" onclick="sortTable(0)">Invoice #</button></th>
                <th><button class="sort-btn" onclick="sortTable(1)">Business</button></th>
                <th><button class="sort-btn" onclick="sortTable(2)">Customer</button></th>
                <th><button class="sort-btn" onclick="sortTable(3)">Amount</button></th>
                <th><button class="sort-btn" onclick="sortTable(4)">Due Date</button></th>
                <th>Amount Difference</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
    """

    # Add rows
    for _, row in df.iterrows():
        # Determine if the difference should be highlighted
        amount_diff_class = (
            "higher-amount"
            if str(row["amount_difference"]).startswith("+")
            else "normal-amount"
        )

        html_content += f"""
            <tr>
                <td>{row['invoice_number']}</td>
                <td>{row['business_name']}</td>
                <td>{row['customer_name']}</td>
                <td>{row['total_amount']}</td>
                <td>{row['due_date']}</td>
                <td class="{amount_diff_class}">{row['amount_difference'] if pd.notna(row['amount_difference']) else 'First Invoice'}</td>
                <td class="action-buttons">
                    <button class="send-reminder" 
                            onclick="sendReminder('{row['customer_email']}', '{row['invoice_number']}', '{row['due_date']}', '{row['total_amount']}')">
                        Send Reminder
                    </button>
                    <button class="pay-button" 
                            onclick="handlePayment('{row['invoice_number']}', '{row['total_amount']}')">
                        Pay
                    </button>
                </td>
            </tr>
        """

    html_content += """
        </tbody>
    </table>
    
    <script>
    function sortTable(n) {
        var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
        table = document.getElementById("invoiceTable");
        switching = true;
        dir = "asc";
        
        while (switching) {
            switching = false;
            rows = table.rows;
            
            for (i = 1; i < (rows.length - 1); i++) {
                shouldSwitch = false;
                x = rows[i].getElementsByTagName("TD")[n];
                y = rows[i + 1].getElementsByTagName("TD")[n];
                
                if (dir == "asc") {
                    if (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) {
                        shouldSwitch = true;
                        break;
                    }
                } else if (dir == "desc") {
                    if (x.innerHTML.toLowerCase() < y.innerHTML.toLowerCase()) {
                        shouldSwitch = true;
                        break;
                    }
                }
            }
            
            if (shouldSwitch) {
                rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                switching = true;
                switchcount++;
            } else {
                if (switchcount == 0 && dir == "asc") {
                    dir = "desc";
                    switching = true;
                }
            }
        }
    }
    
    function sendReminder(email, invoice_number, due_date, amount) {
        window.parent.postMessage({
            type: 'send_reminder',
            email: email,
            invoice_number: invoice_number,
            due_date: due_date,
            amount: amount
        }, '*');
    }

    function handlePayment(invoice_number, amount) {
        window.parent.postMessage({
            type: 'handle_payment',
            invoice_number: invoice_number,
            amount: amount
        }, '*');
    }
    </script>
    """

    return html_content


def calculate_amount_difference(current_amount, previous_amount):
    """Calculate the difference between current and previous amount"""
    if pd.isna(previous_amount):
        return "First Invoice"

    current_value = float(current_amount.replace("CAD $", "").replace(",", ""))
    previous_value = float(previous_amount.replace("CAD $", "").replace(",", ""))

    difference = current_value - previous_value
    return f"{difference:.2f}"


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

    # Ensure due_date is in a sortable format
    if metadata["due_date"] and "On Receipt" not in metadata["due_date"]:
        try:
            metadata["due_date"] = datetime.strptime(
                metadata["due_date"], "%b %d, %Y"
            ).strftime("%Y-%m-%d")
        except ValueError:
            st.warning("Due date format not recognized. Using today's date.")
            metadata["due_date"] = datetime.today().strftime("%Y-%m-%d")

    # Update the session state
    st.session_state.invoices = add_invoice(metadata, st.session_state.invoices)
    st.success("Invoice uploaded and parsed successfully!")

# Display interactive table
st.subheader("Invoice Management Dashboard")
if st.session_state.invoices:
    html_table = create_interactive_table(st.session_state.invoices)
    components.html(html_table, height=600, scrolling=True)
else:
    st.info("No invoices uploaded yet.")

# Download option
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
