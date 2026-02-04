# Risk Score v3.1 Methodology (KRI)

This document details the mathematical model used to calculate the Axur Risk Score.

## The Formula

The Risk Score (0-1000) is an inverse score: **Higher is Better**.

$$
Score = 1000 - (BaseScore \times PenaltyFactors)
$$

Where:
- **BaseScore**: Derived from the volume and severity of confirmed incidents.
- **PenaltyFactors**: Multipliers based on aggravating circumstances (Stealers, Reputation).

---

## 4 Key Risk Indicators (KRIs)

This model calculates the score individually **per brand** (filial).

### 1. Weighted Incidents (45%)

Incidents are weighted by their severity type. Only confirmed incidents (filter by `incident.date`) are counted.

| Threat Type | Weight |
|:---|:---:|
| Ransomware / Stealer Logs | 100 |
| Phishing / Malware | 50 |
| Brand Misuse / Social Profile | 20 |
| Information Leak | 10 |

### 2. Market Benchmark (25%)

We compare your incident volume against the industry average (Brand Median).

- If `Volume < Brand Median`: Bonus to score.
- If `Volume > Brand Median`: Penalty to score.

### 3. Stealer Factor (20% Penalty)

Active stealer logs indicate compromised devices. Even one active log triggers a significant penalty.

### 4. Reputational Impact (10%)

Based on consumer complaints (ReclameAqui, Twitter, etc) related to fraud.

> **Note**: The "Operational Efficiency" KPI has been removed in v3.1 to focus purely on threat exposure and resolution volume.
