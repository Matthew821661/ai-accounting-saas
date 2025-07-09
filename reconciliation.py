
import pandas as pd
from fuzzywuzzy import fuzz

def match_invoices_to_bank(invoices_df, bank_df):
    invoices_df['Matched'] = False
    invoices_df['Matched Txn ID'] = ""
    invoices_df['Match Score'] = 0

    for inv_idx, inv_row in invoices_df.iterrows():
        best_score = 0
        best_match = None
        for bank_idx, bank_row in bank_df.iterrows():
            score = 0
            if abs(inv_row['Amount'] - (bank_row.get('Debit') or 0)) < 5:
                score += 50
            if fuzz.partial_ratio(str(inv_row['Description']), str(bank_row['Description'])) > 70:
                score += 50
            if score > best_score:
                best_score = score
                best_match = bank_row
        if best_match is not None and best_score >= 70:
            invoices_df.at[inv_idx, 'Matched'] = True
            invoices_df.at[inv_idx, 'Matched Txn ID'] = best_match.get('ID', '')
            invoices_df.at[inv_idx, 'Match Score'] = best_score

    summary = invoices_df[['Amount', 'Matched']].groupby('Matched').count().rename(columns={"Amount": "Invoice Count"})
    summary['Status'] = summary.index.map({True: "Matched", False: "Unmatched"})
    return invoices_df, summary.reset_index(drop=True)
