# Axur API - Mock Examples

Este documento proporciona **ejemplos de respuestas simuladas (MOCK)** de la API de Axur para propósitos de testing y demostración, basados en la documentación oficial.

---

## 1. Filtro por Origen de Detección (OnePixel)

### Request
```http
GET /tickets-api/tickets?ticket.customer=ARK&ticket.creation.originator=onepixel&open.date=ge:2025-10-28T00:00:00&open.date=le:2026-01-28T23:59:59&pageSize=200&sortBy=open.date&order=desc
Authorization: Bearer <API_KEY>
```

### Response (MOCK)
```json
{
  "tickets": [
    {
      "key": "PHSH-12345",
      "reference": "https://malicious-phishing.com/login",
      "detection": {
        "type": "phishing",
        "assets": ["SURA"],
        "open": { "date": "2026-01-15T10:23:45Z" }
      },
      "ticket": {
        "creation": {
          "date": "2026-01-15T10:23:45Z",
          "originator": "onepixel",
          "collector": "web-collector"
        }
      },
      "current": {
        "status": "incident",
        "resolution": null,
        "criticality": "high"
      }
    },
    {
      "key": "PHSH-12346",
      "reference": "https://fake-bank-login.net/secure",
      "detection": {
        "type": "phishing",
        "assets": ["AFORE"],
        "open": { "date": "2026-01-10T14:55:12Z" }
      },
      "ticket": {
        "creation": {
          "date": "2026-01-10T14:55:12Z",
          "originator": "onepixel",
          "collector": "one-pixel-tracker"
        }
      },
      "current": {
        "status": "treatment",
        "resolution": null,
        "criticality": "high"
      }
    },
    {
      "key": "FKAP-78901",
      "reference": "https://play.google.com/store/apps/fake-sura",
      "detection": {
        "type": "fake-mobile-app",
        "assets": ["SURA"],
        "open": { "date": "2026-01-08T09:12:33Z" }
      },
      "ticket": {
        "creation": {
          "date": "2026-01-08T09:12:33Z",
          "originator": "onepixel",
          "collector": "app-store-monitor"
        }
      },
      "current": {
        "status": "closed",
        "resolution": "resolved",
        "criticality": "medium"
      }
    }
  ],
  "totalPages": 1,
  "totalElements": 3
}
```

### Interpretación del MOCK
| Campo | Valor | Significado |
|:---|:---|:---|
| `ticket.creation.originator` | `"onepixel"` | El ticket fue detectado por el script OnePixel instalado en la web del cliente |
| `ticket.creation.collector` | `"one-pixel-tracker"` | Identificador del sistema colector específico |
| `detection.type` | `"phishing"`, `"fake-mobile-app"` | Tipo de amenaza detectada |
| `current.status` | `"incident"`, `"treatment"`, `"closed"` | Estado actual del ticket |

---

## 2. Valores Posibles para `ticket.creation.originator`

Según la documentación de Axur (página 3352):

| Valor | Descripción | Ejemplo de Uso |
|:---|:---|:---|
| `onepixel` | Detectado por script de protección OnePixel | Phishing detectado cuando visitante accede a página falsa |
| `platform` | Detectado por la plataforma Axur | Monitoreo proactivo de la plataforma |
| `api` | Insertado manualmente via API | Integración con otros sistemas de seguridad |

---

## 3. Ejemplo de Resumen por Tipo (Output Esperado)

Cuando se ejecuta la opción [6] del menú con origen "onepixel":

```
=================================================================
  FILTRAR POR ORIGEN DE DETECCIÓN
=================================================================

  🔍 Buscando tickets con origen 'onepixel'...

  ✅ Encontrados 3 tickets detectados por ONEPIXEL

  Resumen por Tipo:
    • phishing: 2
    • fake-mobile-app: 1

  Presiona ENTER para continuar...
```

---

## 4. Campos Soportados para Filtros

Según la documentación oficial (líneas 140-242), los campos relacionados con origen son:

```
ticket.creation.originator  (string) - Método de creación del ticket
ticket.creation.collector   (string) - Colector/fuente que identificó la amenaza
ticket.creation.date        (date)   - Fecha de creación
ticket.creation.user        (integer) - Usuario que creó el ticket
```

---

> **Nota:** Estos son datos MOCK para demostración. Los valores reales dependen de los tickets existentes en tu cuenta de Axur.
