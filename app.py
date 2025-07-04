import streamlit as st
import pandas as pd
import pdfplumber
import os
from datetime import datetime
from openai import OpenAI

# Configuration
openai_api_key = os.getenv("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")
client = OpenAI(api_key=openai_api_key)
VAT_RATE = 0.15

def calculate_vat(amount):
    """Return VAT portion of a VAT-inclusive amount."""
    return round(amount * VAT_RATE / (1 + VAT_RATE), 2)

def parse_bank_statement(uploaded_file) -> pd.DataFrame:
    """Read a PDF or Excel bank statement to a DataFrame with Date, Description, Amount."""
    tmp_path = f"/tmp/{uploaded_file.name}"
    with open(tmp_path, "wb") as f:
        f.write(uploaded_file.read())

    if uploaded_file.name.lower().endswith(".pdf"):
        records = []
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if not table:
                    continue
                headers = table[0]
                for row in table[1:]:
                    if row == headers:
                        continue
                    date_str = row[0].strip()
                    try:
                        dt = datetime.strptime(date_str, "%d/%m/%Y")
                    except:
                        continue
                    desc = row[2].strip() if len(row) > 2 and row[2] else ""
                    def to_num(x):
                        if not x:
                            return 0.0
                        return float(x.replace(" ", "").replace(",", "").replace("R", "").replace("ZAR", ""))
                    money_in = to_num(row[3]) if len(row) > 3 else 0.0
                    money_out = to_num(row[4]) if len(row) > 4 else 0.0
                    amt = money_in - money_out
                    records.append({"Date": dt, "Description": desc, "Amount": amt})
        df = pd.DataFrame(records)
    else:
        df = pd.read_excel(tmp_path)

    df = df.rename(columns=lambda c: c.strip())
    if len(df.columns) < 3:
        raise ValueError("Uploaded file must have Date, Description, Amount")
    df.columns = ["Date", "Description", "Amount"] + list(df.columns[3:])
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
    df = df[["Date", "Description", "Amount"]]
    return df

def classify_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Classify transactions into GL accounts using OpenAI."""
    gl_accounts = []
    for _, row in df.iterrows():
        prompt = (
            f"Date: {row['Date'].date()}, "
            f"Description: {row['Description']}, "
            f"Amount: {row['Amount']}. "
            "Classify into a single GL account."
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=32,
        )
        acct = resp.choices[0].message.content.strip()
        gl_accounts.append(acct)
    df["GL Account"] = gl_accounts
    return df

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

def generate_trial_balance(ledger: Ledger) -> pd.DataFrame:
    """Generate a trial balance from a Ledger."""
    df = ledger.to_dataframe()
    tb = df.groupby("Account").agg({"Debit": "sum", "Credit": "sum"}).reset_index()
    tb["Balance"] = tb["Debit"] - tb["Credit"]
    return tb

def main():
    st.title("AI Accounting SaaS — Fixed")

    st.sidebar.header("Upload Bank Statement")
    uploaded = st.sidebar.file_uploader("PDF or Excel", type=["pdf", "xls", "xlsx"])
    if not uploaded:
        st.info("Upload a PDF/Excel bank statement to begin.")
        return

    try:
        df = parse_bank_statement(uploaded)
        st.subheader("Parsed Transactions")
        st.dataframe(df)
    except Exception as e:
        st.error(f"Error parsing statement: {e}")
        return

    if st.button("Classify via AI"):
        with st.spinner("Classifying..."):
            df = classify_transactions(df)
        st.subheader("Classified Transactions")
        st.dataframe(df)

        ledger = Ledger()
        for _, r in df.iterrows():
            amt = r["Amount"]
            if amt >= 0:
                ledger.post(r["Date"], r["GL Account"], debit=amt, narrative=r["Description"])
            else:
                ledger.post(r["Date"], r["GL Account"], credit=-amt, narrative=r["Description"])

        st.subheader("General Ledger")
        st.dataframe(ledger.to_dataframe())

        st.markdown("---")
        st.subheader("Manual / Adjusting Entries")
        with st.form("adjustments"):
            d = st.date_input("Date", datetime.today())
            acct = st.text_input("Account")
            db = st.number_input("Debit", min_value=0.0)
            cr = st.number_input("Credit", min_value=0.0)
            nat = st.text_input("Narrative")
            if st.form_submit_button("Post Entry"):
                ledger.post(d, acct, debit=db, credit=cr, narrative=nat)
                st.success("Posted!")

        tb = generate_trial_balance(ledger)
        st.markdown("---")
        st.subheader("Trial Balance")
        st.dataframe(tb)

        sales = tb[tb["Account"].str.contains("Sales|Revenue", case=False)]["Balance"].sum()
        purchases = tb[tb["Account"].str.contains("Expenses|Purchases", case=False)]["Balance"].sum()
        vat_out = calculate_vat(sales)
        vat_in = calculate_vat(purchases)
        st.markdown(f"**VAT on Outputs:** ZAR {vat_out}")
        st.markdown(f"**VAT on Inputs:** ZAR {vat_in}")
        st.markdown(f"**Net VAT Due:** ZAR {vat_out - vat_in}")

if __name__ == "__main__":
    main()
