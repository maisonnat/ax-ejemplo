# Threat Modeling Architectures

This toolkit implements two standard threat modeling methodologies tailored for Digital Risk Protection (DRP).

---

## 1. DREAD (Prioritization)

DREAD is used to **prioritize** which incidents should be handled first based on risk.

### The 5 Factors

Each factor is scored 1-10.

1. **Damage Potential**: How bad would the attack be?
   - *1*: No damage
   - *10*: Complete systems compromise / Bankruptcy risk
2. **Reproducibility**: How easy is it to reproduce?
   - *1*: Theoretical only
   - *10*: Just click a link
3. **Exploitability**: How much work is it to launch the attack?
   - *1*: Advanced NSA-level skills needed
   - *10*: Script kiddie (automated tools available)
4. **Affected Users**: How many people are impacted?
   - *1*: Single user
   - *10*: All customers / Global
5. **Discoverability**: How easy is it to find the vulnerability?
   - *1*: Obscure source code
   - *10*: Published on main page / Google indexed

### Calculation

$$
RiskScore = \frac{(D + R + E + A + D)}{5}
$$

---

## 2. STRIDE (Classification)

STRIDE is used to **categorize** threats to understand the attacker's strategy.

| Letter | Category | Definition | Axur Examples |
|:---:|:---|:---|:---|
| **S** | **Spoofing** | Pretending to be someone else | Phishing, Fake Social Profiles, Look-alike domains |
| **T** | **Tampering** | Modifying data or code | Fake Mobile Apps, defacement |
| **R** | **Repudiation** | Claiming you didn't do it | Unauthorized transactions (Carding) |
| **I** | **Information Disclosure** | Exposing data | Leaked Credentials, Data Breach, Exposed S3 Buckets |
| **D** | **Denial of Service** | Crashing the system | DDoS, Ransomware demanding payment to restore access |
| **E** | **Elevation of Privilege** | Gaining admin access | Stealer Logs (admin credentials), Rootkits |

### Mapping Strategy

The toolkit automatically maps Axur incident types (e.g., `phishing`, `leak`) to these categories. You can customize this mapping in `use_cases/executive_reports/generator.py`.
