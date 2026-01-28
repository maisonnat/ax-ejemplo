# Axur Risk Assessment Toolkit v4.0

> **Guía completa para implementar sistemas de evaluación de riesgo usando la API de Axur**

Este documento sirve como puente entre la [documentación oficial de Axur](https://docs.axur.com/en/axur/api/) y la implementación práctica de metodologías de riesgo.

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Configuración](#configuración)
3. [Metodologías Implementadas](#metodologías-implementadas)
   - [Risk Score v3.0 (KRI)](#risk-score-v30-kri)
   - [DREAD Analysis](#dread-analysis)
   - [STRIDE Classification](#stride-classification)
4. [Endpoints de la API](#endpoints-de-la-api)
5. [Ejemplos Mock Completos](#ejemplos-mock-completos)
6. [Personalización](#personalización)
7. [Referencias Axur](#referencias-axur)

---

## Resumen Ejecutivo

### ¿Qué hace este toolkit?

| Metodología | Pregunta de Negocio | Salida |
|:---|:---|:---|
| **Risk Score v3.0** | ¿Cómo está mi postura de seguridad general? | Score 0-1000 |
| **DREAD** | ¿Qué incidentes debo atender primero? | Top 10 priorizado |
| **STRIDE** | ¿Qué tipos de ataque me afectan más? | Matriz de amenazas |
| **Credenciales** | ¿Qué credenciales están expuestas? | Lista filtrada por dominio |

### Para quién es este documento

- **👔 Ejecutivos**: Explicaciones de negocio en cada sección
- **💻 Desarrolladores**: Ejemplos de código, JSON mock, y links a documentación técnica

---

## Configuración

### Paso 1: Crear `config.json`

```json
{
  "api_key": "TU_API_KEY_AQUÍ",
  "customer_id": "TU_CUSTOMER_ID",
  "base_url": "https://api.axur.com/gateway/1.0/api",
  "days_range": 30
}
```

### Paso 2: Obtener API Key

1. Accede a [Axur Platform](https://one.axur.com)
2. Ve a **Preferencias** → **API Keys**
3. Crea una nueva API Key con permisos de lectura

> 📖 **Documentación Axur**: [Authentication](https://docs.axur.com/en/axur/api/#section/Authentication)

### Paso 3: Ejecutar

```bash
python mainTest.py
```

---

## Metodologías Implementadas

---

### Risk Score v3.0 (KRI)

#### 👔 Visión de Negocio

> "Dame un número único que resuma qué tan seguro estoy comparado con mi industria"

El Risk Score evalúa tu **postura de seguridad general** en una escala de 0-1000:

| Score | Estado | Significado |
|:---:|:---|:---|
| 800-1000 | 🟢 **EXCELENTE** | Bajo riesgo, mantener monitoreo |
| 600-799 | 🟡 **BUENO** | Riesgo moderado, revisar alertas |
| 400-599 | 🟠 **ALERTA** | Requiere acciones preventivas |
| 0-399 | 🔴 **CRÍTICO** | Atención inmediata necesaria |

#### 💻 Visión Técnica

**Fórmula:**
```
Score = 1000 - (BaseScore × PenaltyFactors)
```

**5 Indicadores (KRIs):**

| KRI | Peso | Endpoint | Uso |
|:---|:---:|:---|:---|
| Volumen Ponderado | 40% | `/stats/incident/count/ticket-types` | Incidentes × peso por gravedad |
| Benchmark Sector | 20% | `/stats/incident/customer/market-segment/median` | Comparar vs industria |
| Stealer Logs | 20% | `/exposure-api/credentials` | Malware activo |
| Eficiencia Ops | 10% | `/stats/takedown/uptime` | Tiempo de resolución |
| Impacto Reputacional | 10% | `/web-complaints/results` | Víctimas reportadas |

---

### DREAD Analysis

#### 👔 Visión de Negocio

> "De todos mis incidentes abiertos, ¿cuáles debo atender primero?"

DREAD prioriza cada incidente individual evaluando su **peligrosidad real**. No es lo mismo un phishing que afecta 5 usuarios que un ransomware que puede paralizar operaciones.

#### 💻 Visión Técnica

DREAD evalúa 5 factores (escala 1-10):

| Factor | Significado | Campo API | Ejemplo |
|:---|:---|:---|:---|
| **D**amage | ¿Cuánto daño puede causar? | `detection.criticality` | high=9, medium=6 |
| **R**eproducibility | ¿Qué tan fácil es replicarlo? | `detection.type` | phishing=9, leak=4 |
| **E**xploitability | ¿Qué tan fácil es explotarlo? | `detection.prediction.risk` | 0.8 → 8 |
| **A**ffected Users | ¿Cuántos usuarios afectados? | `credential.types` | employee=9, user=5 |
| **D**iscoverability | ¿Qué tan público es? | `ticket.creation.collector` | OpenWeb=9, DarkWeb=4 |

**Score Final:**
```python
dread_score = (D + R + E + A + D) / 5
```

**Endpoint Principal:**
```
GET /tickets-api/tickets
```

> 📖 **Documentación Axur**: [Tickets API](https://docs.axur.com/en/axur/api/#tag/Tickets)

---

### Filtro por Origen de Detección (OnePixel)

#### 👔 Visión de Negocio

> "¿Cuántas amenazas fueron detectadas gracias al script OnePixel instalado en nuestra web?"

Esta función permite medir la efectividad del sistema de protección **OnePixel** de Axur, identificando tickets que fueron creados específicamente por este mecanismo de defensa.

#### 💻 Visión Técnica

**Origen de Detección (`ticket.creation.originator`):**

| Valor | Significado |
|:---|:---|
| `onepixel` | Detectado por el script de protección OnePixel |
| `platform` | Detectado por la plataforma Axur |
| `api` | Insertado manualmente via API |
| `collector` | Detectado por colectores específicos |

**Filtrado Eficiente:**
El filtro se aplica a nivel de API (server-side), garantizando alta eficiencia incluso con grandes volúmenes de datos.

---

### STRIDE Classification

#### 👔 Visión de Negocio

> "¿Qué tipos de amenazas me atacan más? ¿Suplantación, fuga de datos, o fraude?"

STRIDE agrupa tus incidentes en **6 categorías estratégicas** para entender dónde concentrar defensas.

#### 💻 Visión Técnica

| Categoría | Descripción | Tipos de Ticket Axur |
|:---|:---|:---|
| **S**poofing | Suplantación de identidad | `phishing`, `fake-social-media-profile`, `similar-domain-name` |
| **T**ampering | Modificación no autorizada | `fraudulent-brand-use`, `fake-mobile-app` |
| **R**epudiation | Negación de acciones | `unauthorized-sale`, `unauthorized-distribution` |
| **I**nfo Disclosure | Fuga de información | `corporate-credential-leak`, `database-exposure`, `code-secret-leak` |
| **D**enial of Service | Interrupción | `ransomware-attack`, `infrastructure-exposure`, `malware` |
| **E**levation | Escalamiento de privilegios | `infostealer-credential`, `executive-credential-leak` |

**Salida Ejemplo:**
```
🔴 [I] Information Disclosure     45 ( 35.2%) ████████
🟠 [S] Spoofing                   32 ( 25.0%) █████
🟡 [E] Elevation of Privilege     28 ( 21.9%) ████
🟡 [D] Denial of Service          15 ( 11.7%) ██
```

---

## Endpoints de la API

### Resumen de Endpoints Utilizados

| Endpoint | Módulo | Documentación |
|:---|:---|:---|
| `/tickets-api/tickets` | DREAD, STRIDE | [Tickets](https://docs.axur.com/en/axur/api/#tag/Tickets) |
| `/tickets-api/stats/incident/count/ticket-types` | Risk Score | [Stats](https://docs.axur.com/en/axur/api/#tag/Stats) |
| `/tickets-api/stats/incident/customer/market-segment/median` | Risk Score | [Stats](https://docs.axur.com/en/axur/api/#tag/Stats) |
| `/tickets-api/stats/takedown/uptime` | Risk Score | [Stats](https://docs.axur.com/en/axur/api/#tag/Stats) |
| `/exposure-api/credentials` | Risk Score, Credenciales | [Exposure API](https://docs.axur.com/en/axur/api/#tag/Exposure-API) |
| `/web-complaints/results` | Risk Score | [Web Complaints](https://docs.axur.com/en/axur/api/#tag/Web-Complaints) |
| `/customers/customers` | Dominios/Marcas | [Customers](https://docs.axur.com/en/axur/api/#tag/Customers) |

### Headers Requeridos

```python
HEADERS = {
    "Authorization": "Bearer TU_API_KEY",
    "Content-Type": "application/json"
}
```

---

## Ejemplos Mock Completos

### 1. Obtener Tickets (DREAD/STRIDE)

**Request:**
```http
GET /tickets-api/tickets?ticket.customer=ACME&status=open,incident&pageSize=50
Authorization: Bearer {API_KEY}
```

**Response Mock:**
```json
{
  "tickets": [
    {
      "ticket": {
        "ticketKey": "ACME-12345",
        "open": {"date": "2024-12-01T10:30:00"},
        "creation": {"collector": "telegram-collector"},
        "reference": "Phishing site mimicking login"
      },
      "detection": {
        "type": "phishing",
        "criticality": "high",
        "prediction": {"risk": 0.85}
      }
    },
    {
      "ticket": {
        "ticketKey": "ACME-12346",
        "creation": {"collector": "darkweb-collector"}
      },
      "detection": {
        "type": "corporate-credential-leak",
        "criticality": "medium",
        "prediction": {"risk": 0.6}
      }
    }
  ],
  "pageable": {"total": 128}
}
```

**Mapeo DREAD:**
- Ticket ACME-12345: D=9, R=9, E=8, A=6, D2=9 → **Score: 8.2** (Alto)
- Ticket ACME-12346: D=6, R=4, E=6, A=7, D2=4 → **Score: 5.4** (Medio)

---

### 2. Estadísticas por Tipo de Incidente (Risk Score)

**Request:**
```http
GET /tickets-api/stats/incident/count/ticket-types?customer=ACME&from=2024-11-01&to=2024-12-01
```

**Response Mock:**
```json
{
  "totalByTicketType": [
    {"type": "phishing", "totalOnPeriod": 45},
    {"type": "fake-social-media-profile", "totalOnPeriod": 23},
    {"type": "corporate-credential-leak", "totalOnPeriod": 18},
    {"type": "ransomware-attack", "totalOnPeriod": 2},
    {"type": "malware", "totalOnPeriod": 5}
  ]
}
```

**Cálculo Volumen Ponderado:**
```
phishing:      45 × 50  = 2,250
fake-profile:  23 × 20  =   460
credential:    18 × 35  =   630
ransomware:     2 × 100 =   200
malware:        5 × 80  =   400
─────────────────────────────
TOTAL PONDERADO:         3,940 pts
```

---

### 3. Benchmark del Sector (Risk Score)

**Request:**
```http
GET /tickets-api/stats/incident/customer/market-segment/median?customer=ACME&to=2024-12-01
```

**Response Mock:**
```json
{
  "marketSegment": "FINANCIAL_INSURANCE",
  "medians": [
    {"total": 42, "referenceMonth": "2024-11"},
    {"total": 38, "referenceMonth": "2024-10"},
    {"total": 45, "referenceMonth": "2024-09"}
  ]
}
```

**Interpretación:**
- Tus incidentes: 93 (suma de totalOnPeriod)
- Mediana sector: 42
- **Ratio: 2.21x** → 🔴 Muy por encima de la media

---

### 4. Credenciales Expuestas

**Request:**
```http
GET /exposure-api/credentials?customer=ACME&status=NEW,IN_TREATMENT&created=ge:2024-11-01&pageSize=50
```

**Response Mock:**
```json
{
  "detections": [
    {
      "user": "john.doe@acme.com",
      "password.type": "PLAIN",
      "leak.format": "STEALER LOG",
      "leak.source": "vidar-logs-2024",
      "created": "2024-11-15T08:30:00"
    },
    {
      "user": "admin@acme.com",
      "password.type": "HASH",
      "leak.format": "COMBOLIST",
      "leak.source": "breach-compilation",
      "created": "2024-11-10T14:20:00"
    }
  ],
  "total": 1542
}
```

**Análisis Crítico:**
- ⚠️ **STEALER LOG detectado**: john.doe@acme.com tiene malware activo
- La contraseña está en **PLAIN** (texto plano) = máxima explotabilidad
- Factor Stealer: **+20%** penalización al Risk Score

> 📖 **Documentación Axur**: [Exposure API Credentials](https://docs.axur.com/en/axur/api/#operation/getCredentials)

---

### 5. Tiempos de Resolución (Eficiencia)

**Request:**
```http
GET /tickets-api/stats/takedown/uptime?customer=ACME&from=2024-11-01&to=2024-12-01
```

**Response Mock:**
```json
{
  "uptime": {
    "lessThan1Day": 1280,
    "upTo2Days": 296,
    "upTo5Days": 535,
    "upTo10Days": 312,
    "upTo15Days": 89,
    "upTo30Days": 78,
    "upTo60Days": 45,
    "over60Days": 12
  }
}
```

**Cálculo Eficiencia:**
```python
total = 2647
slow = 78 + 45 + 12  # > 30 días
efficiency = (total - slow) / total * 100  # = 94.9%
```

---

## Personalización

### Modificar Pesos de Incidentes

Edita `config.json` → `scoring.incident_weights`:

```json
{
  "scoring": {
    "incident_weights": {
      "ransomware-attack": 150,
      "phishing": 30,
      "infostealer-credential": 100
    }
  }
}
```

### Tipos de Incidente Disponibles

Según la [documentación de Axur](https://docs.axur.com/en/axur/api/#section/Fields-supported-by-filters):

```
executive-card-leak, similar-domain-name, executive-personalinfo-leak,
data-sale-website, phishing, executive-credential-leak, unauthorized-distribution,
database-exposure, code-secret-leak, executive-mobile-phone,
suspicious-activity-message, fraud-tool-scheme-message, fraud-tool-scheme-website,
data-sale-message, fake-mobile-app, fraudulent-brand-use, malware,
fake-social-media-profile, corporate-credential-leak, other-sensitive-data,
infostealer-credential, data-exposure-website, executive-fake-social-media-profile,
ransomware-attack, paid-search, suspicious-activity-website,
data-exposure-message, dw-activity, unauthorized-sale, infrastructure-exposure
```

---

## Referencias Axur

### Documentación Oficial

| Recurso | URL |
|:---|:---|
| **Portal Principal** | https://docs.axur.com/en/axur/api/ |
| **OpenAPI Spec** | https://docs.axur.com/en/axur/api/openapi-axur.yaml |
| **Autenticación** | https://docs.axur.com/en/axur/api/#section/Authentication |
| **Tickets API** | https://docs.axur.com/en/axur/api/#tag/Tickets |
| **Stats API** | https://docs.axur.com/en/axur/api/#tag/Stats |
| **Exposure API** | https://docs.axur.com/en/axur/api/#tag/Exposure-API |
| **Customers API** | https://docs.axur.com/en/axur/api/#tag/Customers |

### Límites Técnicos y Manejo de Errores

Es crucial considerar estas limitaciones para evitar errores en producción:

#### 1. Paginación y Límites de Volumen
- **Page Size Máximo:** La API de Tickets (`/tickets-api/tickets`) tiene un **límite estricto de 200 items** por página.
  - *Error Común:* Solicitar `pageSize=500` retorna un error **HTTP 400 Bad Request**.
  - *Solución:* El script implementa un bucle automático que solicita páginas de 200 en 200 hasta obtener todos los resultados en el rango de fechas.

- **Rate Limiting (HTTP 429):**
  - Si recibes un error **429 Too Many Requests**, has excedido la cuota de peticiones.
  - *Mitigación:* Implementar un "backoff exponencial" (esperar unos segundos antes de reintentar).

#### 2. Filtrado de Fechas y Precisión Horaria
- **Precisión:** Para evitar perder incidentes del último día del rango, el script automáticamente añade horas de inicio y fin:
  - `start_date` → `YYYY-MM-DD T00:00:00`
  - `end_date`   → `YYYY-MM-DD T23:59:59`
- **Operadores:** Se usan prefijos `ge:` y `le:` para garantizar la integridad del periodo seleccionado.

#### 3. Filtros de Calidad (Activos vs Descartados)
- **Falsos Positivos:** La plataforma Axur puede marcar incidentes como `resolution: discarded`.
- **Opciones del Script:**
  - **Modo Estándar:** Contabiliza TODO incidente abierto en el periodo (Volumen de Amenaza).
  - **Modo "Solo Activos":** (Nuevo) Permite excluir tickets descartados para alinear el conteo con la vista de "Pendientes" o "Confirmados" del portal.

| Aspecto | Valor / Límite |
|:---|:---|
| **Page Size Máx** | 200 (Tickets API) |
| **Rango Stats Máx** | 90 días |
| **Timeouts** | Recomendado 30s |
| **Benchmark** | Histórico 13 meses |

### Soporte

- [Centro de Ayuda Axur](https://help.axur.com/en/)
- [Plataforma Axur](https://one.axur.com)

---

## Licencia

Este toolkit es un ejemplo de integración. Consulta con Axur para uso en producción.
