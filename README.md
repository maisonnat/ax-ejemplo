# Axur Risk Score v3.0 - Documentación Técnica

## Descripción General

Este script implementa un **Risk Score basado en KRI (Key Risk Indicators)** que evalúa la postura de seguridad de un cliente utilizando los endpoints de la [API de Axur](https://docs.axur.com/en/axur/api/).

El modelo usa **5 indicadores clave** con solo **5 llamadas API** (sin paginación masiva), lo que lo hace eficiente y escalable para cualquier cliente.

---

## Configuración Rápida

### 1. Editar `config.json`

```json
{
  "api_key": "TU_API_KEY_AQUÍ",
  "customer_id": "TU_CUSTOMER_ID",
  "days_range": 30
}
```

### 2. Obtener tu API Key

1. Accede a [Axur Platform](https://one.axur.com)
2. Ve a **Preferencias** → **API Keys**
3. Crea una nueva API Key

### 3. Ejecutar

```bash
python mainTest.py
```

---

## Arquitectura del Risk Score v3.0

### Fórmula Principal

```
Score = 1000 - (BaseScore × PenaltyFactors)
```

Donde:
- `BaseScore = min(500, WeightedIncidents / MarketRatio)`
- `PenaltyFactors = (1 + StealerFactor) × (1 + SlowFactor) × (1 + ReputationalFactor)`

### Escala de Resultados

| Score | Estado | Descripción |
|:---:|:---|:---|
| 800-1000 | 🟢 EXCELENTE | Postura de seguridad sólida |
| 600-799 | 🟡 BUENO | Riesgo moderado, monitorear |
| 400-599 | 🟠 ALERTA | Acciones preventivas recomendadas |
| 0-399 | 🔴 CRÍTICO | Requiere atención inmediata |

---

## Los 5 KRIs (Key Risk Indicators)

### KRI 1: Volumen Ponderado de Incidentes (40%)

**Endpoint:**
```
GET /tickets-api/stats/incident/count/ticket-types
```

**Parámetros:**
| Parámetro | Ejemplo | Descripción |
|:---|:---|:---|
| `customer` | `ACME` | ID del cliente |
| `from` | `2024-01-01` | Fecha inicio (formato `YYYY-MM-DD`) |
| `to` | `2024-01-31` | Fecha fin |
| `ticketTypes` | `phishing,malware` | Tipos a filtrar (opcional) |

**Ejemplo de uso:**
```python
endpoint = f"{BASE_URL}/tickets-api/stats/incident/count/ticket-types"
params = {
    "customer": "SRCL",
    "from": "2024-11-30T00:00:00",
    "to": "2024-12-30T23:59:59"
}
response = requests.get(endpoint, headers=HEADERS, params=params)
```

**Respuesta:**
```json
{
  "totalByTicketType": [
    {"type": "phishing", "totalOnPeriod": 50},
    {"type": "malware", "totalOnPeriod": 3}
  ]
}
```

**Pesos configurables** (en `config.json`):

| Tipo de Incidente | Peso | Justificación |
|:---|:---:|:---|
| `ransomware-attack` | 100 | Máximo impacto |
| `malware` | 80 | Infección activa |
| `infostealer-credential` | 80 | Robo en tiempo real |
| `phishing` | 50 | Suplantación de marca |
| `data-sale-message` | 40 | Datos en venta |
| `fake-social-media-profile` | 20 | Riesgo reputacional |
| Otros | 10 | Bajo impacto |

---

### KRI 2: Benchmark del Sector de Mercado (20%)

**Endpoint:**
```
GET /tickets-api/stats/incident/customer/market-segment/median
```

**Parámetros:**
| Parámetro | Ejemplo | Descripción |
|:---|:---|:---|
| `customer` | `ACME` | La API detecta automáticamente el sector |
| `to` | `2024-12-30` | Fecha de corte (retorna 13 meses hacia atrás) |

**Ejemplo de uso:**
```python
endpoint = f"{BASE_URL}/tickets-api/stats/incident/customer/market-segment/median"
params = {
    "customer": "SRCL",
    "to": "2024-12-30"
}
```

**Respuesta:**
```json
{
  "marketSegment": "FINANCIAL_INSURANCE",
  "medians": [
    {"total": 42, "referenceMonth": "2024-11"},
    {"total": 38, "referenceMonth": "2024-10"}
  ]
}
```

**Interpretación del Ratio:**
```
Ratio = Incidentes_Cliente / Mediana_Sector
```

| Ratio | Interpretación |
|:---:|:---|
| < 0.5 | 🟢 Mejor que pares |
| 0.5 - 1.0 | 🟡 En la media |
| 1.0 - 2.0 | 🟠 Sobre la media |
| > 2.0 | 🔴 Muy por encima |

---

### KRI 3: Stealer Logs (Malware Activo) - CRÍTICO (20%)

**Endpoint:**
```
GET /exposure-api/credentials
```

**Parámetros clave:**
| Parámetro | Valor | Descripción |
|:---|:---|:---|
| `customer` | `ACME` | ID del cliente |
| `status` | `NEW,IN_TREATMENT` | Solo activos |
| `created` | `ge:2024-11-01` | Desde fecha |

**Campos críticos en respuesta:**
- `leak.format`: Si es `"STEALER LOG"`, indica malware activo
- `password.type`: Si es `"PLAIN"`, contraseña en texto plano

**Por qué es crítico:**
- Un **Stealer Log** indica que hay un dispositivo **activamente infectado** robando credenciales
- 1 Stealer Log es más peligroso que 1,000 credenciales de una Combolist vieja

**Factor de penalización:**
| Stealer Logs | Factor |
|:---:|:---|
| 0 | +0% |
| 1-5 | +20% |
| 6-20 | +50% |
| 21+ | +100% |

---

### KRI 4: Eficiencia Operativa (10%)

**Endpoint:**
```
GET /tickets-api/stats/takedown/uptime
```

**Respuesta:**
```json
{
  "uptime": {
    "lessThan1Day": 1280,
    "upTo2Days": 296,
    "upTo5Days": 535,
    "upTo30Days": 78,
    "upTo60Days": 113,
    "over60Days": 5
  }
}
```

**Lógica:**
```python
slow_cases = upTo30Days + upTo60Days + over60Days
efficiency = (total - slow_cases) / total * 100
```

Casos abiertos > 30 días indican **incapacidad operativa** para mitigar amenazas.

---

### KRI 5: Impacto Reputacional (10%)

**Endpoint:**
```
GET /web-complaints/results
```

**Respuesta:**
```json
{
  "totalElements": 5,
  "content": [...]
}
```

Representa **víctimas reales** de fraude que reportaron públicamente. Si hay volumen aquí, el riesgo técnico ya se convirtió en **daño reputacional**.

---

## Personalización de Criterios

### Modificar Pesos de Incidentes

Edita `config.json`:

```json
{
  "scoring": {
    "incident_weights": {
      "ransomware-attack": 150,  // Aumentar peso
      "phishing": 30             // Reducir peso
    }
  }
}
```

### Agregar Nuevos Tipos de Incidente

Consulta los tipos disponibles en la [documentación oficial](https://docs.axur.com/en/axur/api/#section/Fields-supported-by-filters):

```
executive-card-leak, similar-domain-name, data-sale-website, phishing,
database-exposure, code-secret-leak, malware, fake-social-media-profile,
corporate-credential-leak, infostealer-credential, ransomware-attack...
```

---

## Funciones Adicionales

### Consulta de Dominios y Marcas

El script obtiene automáticamente las marcas y dominios del cliente:

```
GET /customers/customers
```

Filtra por `category: "DOMAIN"` y `category: "BRAND"`, mapeando cada dominio a su marca mediante el campo `OFFICIAL_WEBSITE`.

### Consulta de Credenciales Detectadas

Sin consumir créditos (usa Exposure API, no Threat Hunting):

```
GET /exposure-api/credentials
```

**Opciones de filtro:**
- `[0]` Sin filtro (todas)
- `[A]` Todas con dominios del cliente
- `[B]` Por marca
- `[D]` Por dominio específico

---

## Limitaciones y Notas

1. **Rate Limits**: 60 requests/minuto en endpoints de stats
2. **Rango máximo**: 90 días para endpoints de stats
3. **Benchmark**: Usa mediana (más robusta que media)
4. **Exposure API**: No consume créditos de Threat Hunting

---

## Referencias

- [Documentación Oficial Axur API](https://docs.axur.com/en/axur/api/)
- [OpenAPI Spec](https://docs.axur.com/en/axur/api/openapi-axur.yaml)
- [Soporte Axur](https://help.axur.com/en/)
