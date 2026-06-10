# Case Study 3 — Data Audit for Wikipedia Web-Scraped Italian Architects Dataset

**Group B:** Merve Civcik, Hamdi Çakır, Şeyma Olcay
**Date:** April 2026

## About
A six-step data audit performed on the CS2 Wikipedia dataset (211 building records).

## Six Audit Steps
1. Data Consistency Check
2. Missing Data Analysis (MCAR / MAR / MNAR)
3. Outlier Analysis (IQR method)
4. Distribution and Statistical Summary (Mean, Median, Mode, SD, Skewness, Kurtosis)
5. Repeated Data Check
6. Bias Check

## Key Findings
- After cleaning: 0 nulls in country and building_type
- 3 duplicate records removed (211 → 208)
- Architect bias: Renzo Piano (26.4%) and Andrea Palladio (23.1%) dominate
- Geographic bias: Italy 66.3%

## Files in this folder
- `Data_Audit_GroupB.ipynb` (the audit notebook)
- `Data_Audit_Report_GroupB.pdf` (the final PDF report)
- 'dataset.pkl'
- Miro Board Link: https://miro.com/app/board/uXjVG9jvNlY=/
