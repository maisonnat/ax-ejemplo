# Risk Score v3.0 Methodology (KRI)

This document details the mathematical model used to calculate the Axur Risk Score.

## The Formula

The Risk Score (0-1000) is an inverse score: **Higher is Better**.

$$
Score = 1000 - (BaseScore \times PenaltyFactors)
$$

Where:
- **BaseScore**: Derived from the volume and severity of open incidents.
- **PenaltyFactors**: Multipliers based on aggravating circumstances (Stealers, Reputation, Slow Takedown).

---

## 5 Key Risk Indicators (KRIs)

### 1. Weighted Incidents (40%)

Incidents are weighted by their severity type.

| Threat Type | Weight |
|:---|:---:|
| Ransomware / Stealer Logs | 100 |
| Phishing / Malware | 50 |
| Brand Misuse / Social Profile | 20 |
| Information Leak | 10 |

### 2. Market Benchmark (20%)

We compare your incident volume against the industry average.

- If `Volume < Average`: Bonus to score.
- If `Volume > Average`: Penalty to score.

### 3. Stealer Factor (15% Penalty)

Active stealer logs indicate compromised devices. Even one active log triggers a 15% penalty to the score.

### 4. Operational Efficiency (15%)

Measures how fast incidents are resolved (Takedown Time).
- `Time < 24h`: Efficiency Bonus.
- `Time > 72h`: Efficiency Penalty.

### 5. Reputational Impact (10%)

Based on consumer complaints (ReclameAqui, Twitter, etc) related to fraud.
