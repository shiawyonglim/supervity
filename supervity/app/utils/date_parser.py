import pandas as pd
import re

def parse_mixed_date(date_str):
    if pd.isna(date_str) or not date_str:
        return pd.NaT
    date_str = str(date_str).strip()
    
    # ISO: 2026-07-12 00:00:00 or ISO-with-offset: 2026-07-09T00:00:00+08:00
    if re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
        return pd.to_datetime(date_str, errors='coerce', utc=True)
    
    # UK slash format (DD/MM/YYYY)
    elif re.match(r'^\d{2}/\d{2}/\d{4}', date_str):
        return pd.to_datetime(date_str, format='%d/%m/%Y', errors='coerce', utc=True)
    elif re.match(r'^\d{2}/\d{2}/\d{2}', date_str):
        return pd.to_datetime(date_str, format='%d/%m/%y', errors='coerce', utc=True)
        
    # Short-month text (Jul 09 2026)
    elif re.match(r'^[A-Za-z]{3}\s\d{2}\s\d{4}', date_str):
        return pd.to_datetime(date_str, format='%b %d %Y', errors='coerce', utc=True)
        
    # Fallback
    return pd.to_datetime(date_str, errors='coerce', utc=True)
