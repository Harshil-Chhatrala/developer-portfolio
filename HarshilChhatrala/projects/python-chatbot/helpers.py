"""
helpers.py - Core mathematical utility engines, metric scoring systems, 
and dataframe formatting wrappers for the Laptop Recommendation Chatbot.
"""

import random
import re
import pandas as pd
import streamlit as st
import time

def calculate_score(row: pd.Series) -> float:
    """
    Calculates a qualitative structural recommendation score based on hardware technical specifications.
    Formula: (RAM * 5) + (Storage / 128) + GPU_Bonus + Processor_Bonus - (Price / 12000)
    """
    try:
        ram = float(row['ram_gb'])
        storage = float(row['storage_gb'])
        price = float(row['price_inr'])
    except (ValueError, TypeError):
        return 0.0

    # Base formula tracking
    score = (ram * 5.0) + (storage / 128.0)

    # GPU Bonus Calculation
    gpu_str = str(row['gpu']).lower()
    gpu_bonus = 0.0
    if 'rtx' in gpu_str:
        gpu_bonus = 25.0
    elif 'gtx' in gpu_str:
        gpu_bonus = 15.0
    elif 'iris' in gpu_str or 'radeon' in gpu_str:
        gpu_bonus = 8.0
    elif 'm1' in gpu_str or 'm2' in gpu_str or 'apple' in gpu_str:
        gpu_bonus = 20.0
    score += gpu_bonus

    # Processor Bonus Calculation
    proc_str = str(row['processor']).lower()
    proc_bonus = 0.0
    if 'i9' in proc_str or 'ryzen 9' in proc_str or 'm2 pro' in proc_str:
        proc_bonus = 30.0
    elif 'i7' in proc_str or 'ryzen 7' in proc_str or 'm1' in proc_str or 'm2' in proc_str:
        proc_bonus = 20.0
    elif 'i5' in proc_str or 'ryzen 5' in proc_str:
        proc_bonus = 10.0
    score += proc_bonus

    # Price Penalty normalization
    price_penalty = price / 12000.0
    score -= price_penalty

    return round(score, 2)

def get_rating(row: pd.Series) -> str:
    """Calculates a localized star rating system determined by raw tier performance metrics."""
    try:
        ram = int(row['ram_gb'])
        proc = str(row['processor']).lower()
    except (ValueError, TypeError):
        return "⭐⭐⭐"

    if ram >= 16 and ('i7' in proc or 'i9' in proc or 'ryzen 7' in proc or 'ryzen 9' in proc or 'm1' in proc or 'm2' in proc):
        return "⭐⭐⭐⭐⭐"
    elif ram >= 16 or ('i5' in proc or 'ryzen 5' in proc):
        return "⭐⭐⭐⭐"
    else:
        return "⭐⭐⭐"

def match_percentage(score: float) -> int:
    """Normalizes raw configuration scores into a percentage metric bounded between 65% and 99%."""
    clamped_score = max(0.0, min(score, 100.0))
    percentage = int(65 + (clamped_score / 100.0) * 34)
    return min(percentage, 99)

def recommendation_reason(row: pd.Series) -> list:
    """Generates a dynamic list of structured bullet points highlighting design merits."""
    reasons = []
    
    # RAM Check
    if int(row['ram_gb']) >= 16:
        reasons.append(f"✔ {row['ram_gb']}GB RAM (High-Performance Multitasking)")
    else:
        reasons.append(f"✔ {row['ram_gb']}GB RAM (Standard Workplace Utility)")

    # Storage Check
    st_type = str(row['storage_type']).upper()
    reasons.append(f"✔ {row['storage_gb']}GB {st_type} High-Speed Storage")

    # Graphics Check
    gpu_str = str(row['gpu'])
    if 'RTX' in gpu_str.upper() or 'GTX' in gpu_str.upper():
        reasons.append(f"✔ Dedicated {gpu_str} Graphics Engine")
    else:
        reasons.append(f"✔ Integrated {gpu_str} Silicon Rendering")

    # Processor Check
    reasons.append(f"✔ {row['processor']} Central Processing Core")

    # Value Tier Assessment
    price = float(row['price_inr'])
    ram = int(row['ram_gb'])
    if price < 60000 and ram >= 16:
        reasons.append("✔ Budget Champion (Excellent Cost-to-Performance Ratio)")
    elif price > 120000:
        reasons.append("✔ Premium Elite Tier Build Quality")
    else:
        reasons.append("✔ Solid High-Value Strategic Purchase Target")

    return reasons

def laptop_of_the_day(df: pd.DataFrame) -> pd.Series:
    """Returns a highly rated laptop utilizing a random selection pool."""
    if df.empty:
        return None
    
    # Target solid mainstream options for daily display
    high_tier = df[df['ram_gb'] >= 16]
    if not high_tier.empty:
        return high_tier.sample(n=1).iloc[0]
    return df.sample(n=1).iloc[0]

def surprise_me(df: pd.DataFrame) -> pd.DataFrame:
    """Returns a singular isolated random record inside a valid DataFrame wrapper structure."""
    if df.empty:
        return pd.DataFrame()
    return df.sample(n=1)

def cheapest_laptop(df: pd.DataFrame) -> pd.DataFrame:
    """Filters database to output the lowest priced machine currently tracked inside the catalog."""
    if df.empty:
        return pd.DataFrame()
    lowest_price = df['price_inr'].min()
    return df[df['price_inr'] == lowest_price].head(1)

def expensive_laptop(df: pd.DataFrame) -> pd.DataFrame:
    """Isolates the highest pricing ceiling target tracked inside the inventory system."""
    if df.empty:
        return pd.DataFrame()
    highest_price = df['price_inr'].max()
    return df[df['price_inr'] == highest_price].head(1)

def best_value(df: pd.DataFrame) -> pd.DataFrame:
    """Isolates value models by cross-evaluating low-cost metrics against performance scaling rules."""
    if df.empty:
        return pd.DataFrame()
    
    temp_df = df.copy()
    temp_df['eval_score'] = temp_df.apply(calculate_score, axis=1)
    
    # Value factor defined by higher scoring configurations combined with friendly budget entry limits
    value_tier = temp_df[temp_df['price_inr'] <= 75000]
    if value_tier.empty:
        value_tier = temp_df

    best_index = value_tier['eval_score'].idxmax()
    return df.loc[[best_index]]

def compare_laptops(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """
    Parses natural language requests using extraction lookups to present side-by-side comparative views.
    Examples matched: 'compare Dell Inspiron and HP Pavilion', 'MacBook Air M1 vs XPS 13'
    """
    if df.empty:
        return pd.DataFrame()

    # Pattern variants for matching comparisons
    pattern_vs = re.compile(r'compare\s+(.+)\s+vs\s+(.+)', re.IGNORECASE)
    pattern_and = re.compile(r'compare\s+(.+)\s+and\s+(.+)', re.IGNORECASE)
    pattern_direct_vs = re.compile(r'(.+)\s+vs\s+(.+)', re.IGNORECASE)

    m1 = pattern_vs.search(query)
    m2 = pattern_and.search(query)
    m3 = pattern_direct_vs.search(query) if not (m1 or m2) else None

    match = m1 or m2 or m3
    if not match:
        return pd.DataFrame()

    term_a = match.group(1).strip().lower()
    term_b = match.group(2).strip().lower()

    # Cleanup trigger keywords if caught in strings
    term_a = re.sub(r'^compare\s+', '', term_a, flags=re.IGNORECASE).strip()

    def scoring_match(row: pd.Series, check_term: str) -> int:
        full_identity = f"{row['brand']} {row['model']}".lower()
        score = 0
        if check_term in full_identity:
            score += 10
        # Tokenize checking for multi-word sub-matches
        tokens = check_term.split()
        for t in tokens:
            if t in full_identity:
                score += 2
            if t in str(row['processor']).lower():
                score += 1
        return score

    df_copy = df.copy()
    df_copy['score_a'] = df_copy.apply(lambda r: scoring_match(r, term_a), axis=1)
    df_copy['score_b'] = df_copy.apply(lambda r: scoring_match(r, term_b), axis=1)

    matched_rows = []
    
    # Isolate top-scoring records for each comparison branch
    best_a = df_copy[df_copy['score_a'] > 0].sort_values(by='score_a', ascending=False)
    best_b = df_copy[df_copy['score_b'] > 0].sort_values(by='score_b', ascending=False)

    if not best_a.empty:
        matched_rows.append(best_a.iloc[0].name)
    if not best_b.empty:
        matched_rows.append(best_b.iloc[0].name)

    # Deduplicate matching tracks if queries overlap completely
    matched_rows = list(dict.fromkeys(matched_rows))

    if not matched_rows:
        return pd.DataFrame()

    return df.loc[matched_rows]

def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Prepares catalog columns into cleanly structured, end-user facing reporting views."""
    if df.empty:
        return df
    
    display_df = df.copy()
    # Format headers for visual appeal
    display_df.columns = [col.replace('_', ' ').title() for col in display_df.columns]
    if 'Id' in display_df.columns:
        display_df = display_df.drop(columns=['Id'])
        
    return display_df

def typing_effect(text: str, container=None, delay: float = 0.01):
    """Generates progressive character rendering to simulate authentic conversational patterns."""
    displayed_str = ""
    if container is None:
        container = st.empty()
        
    for char in text:
        displayed_str += char
        container.markdown(displayed_str + "▌")
        time.sleep(delay)
        
    container.markdown(displayed_str)