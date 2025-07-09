import pandas as pd
def generate_trial_balance(df):
    df['Debit'] = df['Amount'].apply(lambda x: x if x > 0 else 0)
    df['Credit'] = df['Amount'].apply(lambda x: -x if x < 0 else 0)
    return df.groupby('GL Account')[['Debit', 'Credit']].sum().reset_index()