# Risk Score Methodology (v3.0 & v4.0)

This document details the mathematical models used to calculate the Axur Risk Score.

---

## Overview

The Risk Score (0-1000) is an **inverse score**: **Higher is Better**.

$$
Score = 1000 - (BaseScore \times PenaltyFactors)
$$

Where:
- **BaseScore**: Derived from the volume and severity of open incidents.
- **PenaltyFactors**: Multipliers based on aggravating circumstances.

| Version | Calculation Type | Key Change |
|:---:|:---|:---|
| **v3.0** | Aggregate (All Brands) | 5 KRIs including Efficiency |
| **v4.0** | Per-Brand (Individual) | 4 KRIs, Efficiency Removed |

---

## v4.0 Key Risk Indicators (4 KRIs)

> **Note:** v4.0 removes Operational Efficiency and redistributes its weight.

### 1. Weighted Incidents (45% - was 40%)

Incidents are weighted by their severity type.

| Threat Type | Weight |
|:---|:---:|
| Ransomware / Stealer Logs | 100 |
| Corporate Credential Leak | 60 |
| Phishing / Malware | 50 |
| Fake Mobile App | 40 |
| Brand Misuse | 20 |
| Similar Domain | 15 |

### 2. Market Benchmark (25% - was 20%)

Compare incident volume against industry baseline (100 incidents = median).

- `Volume < Median`: Bonus to score.
- `Volume > Median`: Penalty to score.

### 3. Stealer Factor (20% - was 15%)

Active stealer logs indicate compromised devices.

| Stealer Count | Penalty |
|:---:|:---:|
| 0 | 0% |
| 1-5 | +20% |
| 6-20 | +50% |
| 20+ | +100% |

### 4. Reputational Impact (10% - unchanged)

Based on consumer complaints related to fraud.

---

## v4.0 Per-Brand Calculation

In v4.0, the score is calculated **individually for each brand/subsidiary**:

```
For each brand in tenant:
    1. Filter tickets belonging to that brand
    2. Calculate its own Weighted Incidents
    3. Calculate its own Benchmark Ratio
    4. Calculate its own Stealer Factor
    5. Calculate its own Reputational Impact
    6. Output individual Score + Grade
```

This provides visibility into which subsidiaries have the highest risk.

---

## Grade Scale

| Score | Grade | Status |
|:---:|:---:|:---|
| 850-1000 | A | 🟢 Excellent |
| 700-849 | B | 🟡 Good |
| 550-699 | C | 🟠 Moderate |
| 400-549 | D | 🔴 High Risk |
| 0-399 | F | ⛔ Critical |

---

## Legacy: v3.0 Methodology

v3.0 included 5 KRIs with Operational Efficiency (15%) measuring takedown resolution time. This has been removed in v4.0 per client request.

See `use_cases/risk_scoring/calculator.py` for v3.0 implementation.
See `use_cases/risk_scoring/calculator_v4.py` for v4.0 implementation.
