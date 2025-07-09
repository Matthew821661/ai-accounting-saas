import streamlit as st
import pandas as pd
import sys
import os

# ✅ Fix import path to reach utils folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.classifier import classify_transaction
from utils.vat_engine import calculate_vat
from utils.trial_balance import generate_trial_balance
from utils.reconciliation import match_invoices_to_bank

st.set_page_config(page_title="Matthew Bookkeeping", layout="wide")
st.title("📊 Matthew Bookkeeping")

user = {"email": "demo@user.com"}
st.success(f"✅ Logged in as: {user['email']}")

menu = st.sidebar.selectbox("📂 Menu", ["Bank Upload", "Invoice Reconciliation"])

if menu == "Bank Upload":
    st.header("🏦 Upload Bank Statement")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        df['GL Account'] = df['Description'].apply(classify_transaction)
        df['Amount'] = df['Debit'].fillna(0) - df['Credit'].fillna(0)
        df[['VAT Amount', 'VAT Type']] = df.apply(
            lambda row: pd.Series(calculate_vat(row['Amount'], "standard" if row['GL Account'].startswith("6") else "zero")),
            axis=1
        )
        st.subheader("📄 Transactions")
        st.dataframe(df)
        st.subheader("📊 Trial Balance")
        tb = generate_trial_balance(df)
        st.dataframe(tb)

elif menu == "Invoice Reconciliation":
    st.header("🧾 Upload Invoice + Bank CSVs")
    invoice_file = st.file_uploader("Upload Invoice CSV", type=["csv"])
    bank_file = st.file_uploader("Upload Bank CSV", type=["csv"])
    if invoice_file and bank_file:
        invoices = pd.read_csv(invoice_file)
        bank = pd.read_csv(bank_file)
        st.subheader("📥 Invoices")
        st.dataframe(invoices)
        st.subheader("🏦 Bank Transactions")
        st.dataframe(bank)
        result_df, summary = match_invoices_to_bank(invoices, bank)
        st.subheader("🤖 Reconciliation Results")
        st.dataframe(result_df)
        st.subheader("📊 Summary")
        st.dataframe(summary)
        st.download_button("⬇️ Download Reconciliation CSV", result_df.to_csv(index=False), "reconciliation.csv")
