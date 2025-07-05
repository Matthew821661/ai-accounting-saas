import streamlit as st
import pandas as pd
import pdfplumber
import os
from datetime import datetime
from openai import OpenAI

# Load API key from environment variable
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("Please set the OPENAI_API_KEY environment variable.")
    st.stop()

client = OpenAI(api_key=api_key)
VAT_RATE = 0.15

def calculate_vat(amount: float) -> float:
    return round(amount * VAT_RATE / (1 + VAT_RATE), 2)

def parse_bank_statement(uploaded_file) -> pd.DataFrame:
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
                    desc = row[2] if len(row) > 2 else ""
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

    df.rename(columns=lambda c: c.strip(), inplace=True)
    if df.shape[1] < 3:
        raise ValueError("Statement must have Date, Description, Amount columns.")
    df.columns = ["Date", "Description", "Amount"] + list(df.columns[3:])
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
    return df[["Date", "Description", "Amount"]]

def classify_transactions(df: pd.DataFrame) -> pd.DataFrame:
    gl_accounts = []
    for _, r in df.iterrows():
        prompt = f"Date: {r['Date'].date()}, Description: {r['Description']}, Amount: {r['Amount']}. Classify into a single GL account."
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}],
            temperature=0.0,
            max_tokens=32,
        )
        gl_accounts.append(resp.choices[0].message.content.strip())
    df["GL Account"] = gl_accounts
    return df

class Ledger:
    def __init__(self):
        self.entries = []
    def post(self, date, account, debit=0.0, credit=0.0, narrative=""):
        self.entries.append({
            "Date": date, "Account": account,
            "Debit": debit, "Credit": credit, "Narrative": narrative
        })
    def to_dataframe(self):
        return pd.DataFrame(self.entries)

def trial_balance(ledger: Ledger) -> pd.DataFrame:
    df = ledger.to_dataframe()
    tb = df.groupby("Account").agg({"Debit":"sum","Credit":"sum"}).reset_index()
    tb["Balance"] = tb["Debit"] - tb["Credit"]
    return tb

def main():
    st.title("AI Accounting SaaS")

    st.sidebar.header("Upload Bank Statement")
    uploaded = st.sidebar.file_uploader("PDF or Excel", type=["pdf","xls","xlsx"])
    if not uploaded:
        return

    try:
        df = parse_bank_statement(uploaded)
        st.subheader("Parsed Transactions")
        st.dataframe(df)
    except Exception as e:
        st.error(f"Parsing error: {e}")
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
        st.subheader("Adjusting Entries")
        with st.form("adj"):
            d = st.date_input("Date", datetime.today())
            acct = st.text_input("Account")
            db = st.number_input("Debit", min_value=0.0)
            cr = st.number_input("Credit", min_value=0.0)
            nat = st.text_input("Narrative")
            if st.form_submit_button("Post"):
                ledger.post(d, acct, debit=db, credit=cr, narrative=nat)
                st.success("Posted!")

        tb = trial_balance(ledger)
        st.subheader("Trial Balance")
        st.dataframe(tb)

        sales = tb[tb["Account"].str.contains("Sales|Revenue",case=False)]["Balance"].sum()
        purchases = tb[tb["Account"].str.contains("Expenses|Purchases",case=False)]["Balance"].sum()
        vat_out = calculate_vat(sales)
        vat_in = calculate_vat(purchases)
        st.markdown(f"**VAT on Outputs:** ZAR {vat_out}")
        st.markdown(f"**VAT on Inputs:** ZAR {vat_in}")
        st.markdown(f"**Net VAT Due:** ZAR {vat_out - vat_in}")

if __name__ == "__main__":
    main()
