import streamlit as st
import pandas as pd
import tabula
import os
from datetime import datetime
import openai

# Configuration: set your OpenAI API key as an environment variable
openai.api_key = os.getenv("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")

# -------------------------
# VAT & Tax Rules (South Africa)
# -------------------------
VAT_RATE = 0.15  # 15% standard VAT rate
INCOME_TAX_RATE = 0.28  # 28% corporate income tax (placeholder)

# -------------------------
# Helper Functions
# -------------------------
def calculate_vat(amount: float) -> float:
    """Calculate VAT portion from a VAT-inclusive amount."""
    return round(amount * VAT_RATE / (1 + VAT_RATE), 2)

def net_amount(vat_inclusive: float) -> float:
    """Calculate net amount excluding VAT."""
    return round(vat_inclusive / (1 + VAT_RATE), 2)

# -------------------------
# Bank Statement Parsing
# -------------------------
def parse_bank_statement(uploaded_file) -> pd.DataFrame:
    """
    Reads an uploaded PDF or Excel bank statement and returns a DataFrame with
    columns: Date, Description, Amount
    """
    filename = uploaded_file.name.lower()
    if filename.endswith(".pdf"):
        tmp_path = f"/tmp/{uploaded_file.name}"
        with open(tmp_path, "wb") as f:
            f.write(uploaded_file.read())
        dfs = tabula.read_pdf(tmp_path, pages="all", multiple_tables=True)
        df = pd.concat(dfs, ignore_index=True)
    else:
        df = pd.read_excel(uploaded_file)
    df = df.rename(columns=lambda x: x.strip())
    df = df[["Date", "Description", "Amount"]]
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
    return df

# -------------------------
# AI-based Classification
# -------------------------
def classify_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classify each transaction into a general ledger account using OpenAI.
    Adds a column 'GL Account'.
    """
    responses = []
    for _, row in df.iterrows():
        prompt = f"Date: {row['Date'].date()}, Desc: {row['Description']}, Amount: {row['Amount']}. Classify into one GL account."
        res = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0, max_tokens=32
        )
        responses.append(res.choices[0].message.content.strip())
    df["GL Account"] = responses
    return df

# -------------------------
# Ledger Model
# -------------------------
class Ledger:
    def __init__(self):
        self.entries = []

    def post(self, date, account, debit=0.0, credit=0.0, narrative=""):
        self.entries.append({
            "Date": date,
            "Account": account,
            "Debit": debit,
            "Credit": credit,
            "Narrative": narrative
        })

    def to_dataframe(self):
        return pd.DataFrame(self.entries)

# -------------------------
# Trial Balance Generation
# -------------------------
def generate_trial_balance(ledger: Ledger) -> pd.DataFrame:
    df = ledger.to_dataframe()
    tb = df.groupby("Account").agg({"Debit": "sum", "Credit": "sum"}).reset_index()
    tb["Balance"] = tb["Debit"] - tb["Credit"]
    return tb

# -------------------------
# Streamlit App
# -------------------------
def main():
    st.title("AI Accounting SaaS – Better than Xero & Sage")

    st.sidebar.header("1. Upload Bank Statement")
    uploaded_file = st.sidebar.file_uploader("Upload PDF or Excel", type=["pdf", "xls", "xlsx"])
    if not uploaded_file:
        return

    df = parse_bank_statement(uploaded_file)
    st.write("## Parsed Transactions")
    st.dataframe(df)

    if st.button("Classify via AI"):
        df = classify_transactions(df)
        st.write("## Classified Transactions")
        st.dataframe(df)

        # Initialize ledger and auto-post
        ledger = Ledger()
        for _, r in df.iterrows():
            amt = r["Amount"]
            if amt >= 0:
                ledger.post(r["Date"], r["GL Account"], debit=amt, narrative=r["Description"])
            else:
                ledger.post(r["Date"], r["GL Account"], credit=-amt, narrative=r["Description"])
        st.write("## General Ledger")
        st.dataframe(ledger.to_dataframe())

        # Manual / Adjusting Entries
        st.write("---")
        st.write("## Manual / Adjusting Entries")
        with st.form("adjust_form"):
            d = st.date_input("Date", datetime.today())
            acct = st.text_input("Account")
            db = st.number_input("Debit", min_value=0.0)
            cr = st.number_input("Credit", min_value=0.0)
            nat = st.text_input("Narrative")
            if st.form_submit_button("Post"):
                ledger.post(d, acct, debit=db, credit=cr, narrative=nat)
                st.success("Posted!")

        # Trial Balance
        tb = generate_trial_balance(ledger)
        st.write("---")
        st.write("## Trial Balance")
        st.dataframe(tb)

        # VAT Summary
        sales = tb[tb["Account"].str.contains("Sales|Revenue", case=False)]["Balance"].sum()
        purchases = tb[tb["Account"].str.contains("Expenses|Purchases", case=False)]["Balance"].sum()
        vat_out = calculate_vat(sales)
        vat_in = calculate_vat(purchases)
        st.write(f"VAT on Outputs: ZAR {vat_out}")
        st.write(f"VAT on Inputs: ZAR {vat_in}")
        st.write(f"Net VAT Due: ZAR {vat_out - vat_in}")

if __name__ == "__main__":
    main()
