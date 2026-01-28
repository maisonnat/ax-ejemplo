# Axur Risk Assessment Toolkit v4.0

> **Complete guide to implementing risk assessment systems using the Axur API**

This document bridges the gap between [Axur's official documentation](https://docs.axur.com/en/axur/api/) and practical risk methodology implementation.

🌐 **Language**: [Español](README.md) | **English** | [Português](README.pt.md)

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Setup](#setup)
3. [Implemented Methodologies](#implemented-methodologies)
   - [Risk Score v3.0 (KRI)](#risk-score-v30-kri)
   - [DREAD Analysis](#dread-analysis)
   - [STRIDE Classification](#stride-classification)
4. [Project Structure](#project-structure)
5. [API Endpoints](#api-endpoints)
6. [Mock Examples](#mock-examples)
7. [Customization](#customization)

---

## Executive Summary

### What does this toolkit do?

| Methodology | Business Question | Output |
|:---|:---|:---|
| **Risk Score v3.0** | How is my overall security posture? | Score 0-1000 |
| **DREAD** | Which incidents should I address first? | Prioritized Top 10 |
| **STRIDE** | What attack types affect me most? | Threat matrix |
| **Credentials** | Which credentials are exposed? | Domain-filtered list |
| **OnePixel Filter** | Which threats were auto-detected? | Tickets by origin |

### Who is this for?

- **👔 Executives**: Business explanations in each section
- **💻 Developers**: Code examples, mock JSON, and technical documentation links

---

## Setup

### Step 1: Clone the repository

```bash
git clone https://github.com/yourusername/axur-risk-toolkit.git
cd axur-risk-toolkit
```

### Step 2: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Create `config.json`

```json
{
  "api_key": "YOUR_API_KEY_HERE",
  "customer_id": "YOUR_CUSTOMER_ID",
  "base_url": "https://api.axur.com/gateway/1.0/api",
  "days_range": 30
}
```

### Step 4: Get your API Key

1. Access [Axur Platform](https://one.axur.com)
2. Go to **Preferences** → **API Keys**
3. Create a new API Key with read permissions

> 📖 **Axur Documentation**: [Authentication](https://docs.axur.com/en/axur/api/#section/Authentication)

### Step 5: Run

```bash
python main.py
```

---

## Implemented Methodologies

### Risk Score v3.0 (KRI)

#### 👔 Business View

> "Give me a single number that summarizes how secure I am compared to my industry"

The Risk Score evaluates your **overall security posture** on a 0-1000 scale:

| Score | Status | Meaning |
|:---:|:---|:---|
| 800-1000 | 🟢 **EXCELLENT** | Low risk, maintain monitoring |
| 600-799 | 🟡 **GOOD** | Moderate risk, review alerts |
| 400-599 | 🟠 **ALERT** | Requires preventive actions |
| 0-399 | 🔴 **CRITICAL** | Immediate attention needed |

#### 💻 Technical View

**Formula:**
```
Score = 1000 - (BaseScore × PenaltyFactors)
```

**5 Key Risk Indicators (KRIs):**

| KRI | Weight | Endpoint | Purpose |
|:---|:---:|:---|:---|
| Weighted Incidents | 40% | `/tickets-api/tickets` | Volume and severity |
| Market Benchmark | 20% | `/tickets-api/stats` | Industry comparison |
| Stealer Logs | 15% | `/exposure-api` | Active malware |
| Operational Efficiency | 15% | `/tickets-api/stats/takedown` | Resolution speed |
| Reputational Impact | 10% | `/web-complaints` | Victim reports |

---

### DREAD Analysis

#### 👔 Business View

> "Prioritize my incident queue by real risk"

DREAD evaluates each incident with 5 factors (1-10 scale):

- **D**amage: How much damage could it cause?
- **R**eproducibility: How easy is it to replicate?
- **E**xploitability: How easy is it to exploit?
- **A**ffected users: How many users impacted?
- **D**iscoverability: How easy is it to discover?

Total Score = Average of 5 factors (1-10)

---

### STRIDE Classification

#### 👔 Business View

> "What are their main attack strategies against us?"

STRIDE groups threats into 6 strategic categories:

| Category | Description | Examples |
|:---:|:---|:---|
| **S**poofing | Identity impersonation | Phishing, fake profiles |
| **T**ampering | Data modification | Fake apps, brand misuse |
| **R**epudiation | Deniability | Unauthorized sales |
| **I**nfo Disclosure | Data leaks | Credential leaks, DB exposure |
| **D**enial of Service | Disruption | Ransomware, malware |
| **E**levation | Privilege escalation | Stealer logs |

---

## Project Structure

```
/
├── main.py                 # Main application (interactive menu)
├── config.json             # Configuration (not tracked)
├── requirements.txt        # Python dependencies
│
├── /core                   # Infrastructure layer
│   ├── axur_client.py      # Reusable Axur API connector
│   └── utils.py            # Shared utilities
│
├── /use_cases              # Business logic modules
│   ├── /risk_scoring       # Risk Score v3.0 calculation
│   ├── /threat_detection   # OnePixel origin filter
│   └── /executive_reports  # DREAD + STRIDE analysis
│
└── MOCK_EXAMPLES.md        # API response examples
```

---

## API Endpoints

| Endpoint | Purpose | Documentation |
|:---|:---|:---|
| `/tickets-api/tickets` | Fetch incident tickets | [Link](https://docs.axur.com/en/axur/api/#tag/Tickets) |
| `/tickets-api/stats` | Statistics and metrics | [Link](https://docs.axur.com/en/axur/api/#tag/Stats) |
| `/exposure-api/credentials` | Exposed credentials | [Link](https://docs.axur.com/en/axur/api/#tag/Exposure) |
| `/customers/customers` | Customer assets/brands | [Link](https://docs.axur.com/en/axur/api/#tag/Customers) |

---

## Mock Examples

See [MOCK_EXAMPLES.md](MOCK_EXAMPLES.md) for complete API response examples.

### OnePixel Detection Filter

```python
from use_cases.threat_detection import filter_by_origin

# Get tickets detected by OnePixel
tickets = filter_by_origin(origin="onepixel", days_back=90)
print(f"Found {len(tickets)} OnePixel detections")
```

---

## Customization

### Adding new threat weights

Edit `use_cases/risk_scoring/calculator.py`:

```python
THREAT_WEIGHTS = {
    "ransomware-attack": 100,
    "phishing": 50,
    "your-custom-type": 75,  # Add your custom weight
    ...
}
```

### Adding new STRIDE mappings

Edit `use_cases/executive_reports/generator.py`:

```python
STRIDE_MAPPING = {
    "your-custom-type": "S",  # Map to Spoofing
    ...
}
```

---

## License

This project is for educational and demonstration purposes. Please ensure compliance with Axur's API terms of service.

---

*Built with ❤️ for security teams*
