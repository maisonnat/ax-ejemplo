# Axur API Reference & Mock Examples

This document provides technical details on the Axur API endpoints used in this toolkit, along with mock responses for testing and development.

---

## Endpoints Used

| Endpoint | Method | Description | Documentation |
|:---|:---|:---|:---|
| `/tickets-api/tickets` | GET | List incidents/tickets | [Tickets API](https://docs.axur.com/en/axur/api/#tag/Tickets) |
| `/tickets-api/stats` | GET | Get ticket statistics | [Stats API](https://docs.axur.com/en/axur/api/#tag/Stats) |
| `/exposure-api/credentials` | GET | List exposed credentials | [Exposure API](https://docs.axur.com/en/axur/api/#tag/Exposure) |
| `/customers/customers` | GET | List customer assets | [Customers API](https://docs.axur.com/en/axur/api/#tag/Customers) |
| `/web-complaints/results` | GET | Check victim complaints | [Complaints API](https://docs.axur.com/en/axur/api) |

---

## Mock Examples

Below are simulated responses for key scenarios, useful for understanding the data structure without live API access.

### 1. OnePixel Detection (Origin Filter)

**Scenario:** Detecting phishing attacks identified specifically by the OnePixel script installed on the client's website.

**Request:**
```http
GET /tickets-api/tickets?ticket.creation.originator=onepixel
```

**Response:**
```json
{
  "tickets": [
    {
      "key": "PHSH-12345",
      "reference": "https://malicious-phishing.com/login",
      "detection": {
        "type": "phishing",
        "assets": ["BrandX"],
        "open": { "date": "2026-01-15T10:23:45Z" }
      },
      "ticket": {
        "creation": {
          "date": "2026-01-15T10:23:45Z",
          "originator": "onepixel",
          "collector": "web-collector"
        },
        "ticketKey": "PHSH-12345"
      },
      "current": {
        "status": "incident",
        "resolution": null,
        "criticality": "high"
      }
    },
    {
      "key": "FKAP-78901",
      "reference": "https://play.google.com/store/apps/fake-brand",
      "detection": {
        "type": "fake-mobile-app",
        "assets": ["BrandX"],
        "open": { "date": "2026-01-08T09:12:33Z" }
      },
      "ticket": {
        "creation": {
          "date": "2026-01-08T09:12:33Z",
          "originator": "onepixel",
          "collector": "app-store-monitor"
        }
      }
    }
  ],
  "totalPages": 1,
  "totalElements": 2
}
```

### 2. Detection Origin Values

According to Axur documentation, the `ticket.creation.originator` field can have these values:

| Value | Description |
|:---|:---|
| `onepixel` | Detected by OnePixel protection script |
| `platform` | Detected by Axur platform monitoring |
| `api` | Manually inserted via API integration |
| `collector` | Detected by specific collector subsystem |

---

### 3. Credential Leak Response (Exposure API)

**Request:**
```http
GET /exposure-api/credentials?status=NEW
```

**Response:**
```json
{
  "detections": [
    {
      "id": "exp-001",
      "leak": {
        "format": "STEALER LOG",
        "source": "Dark Web"
      },
      "password": {
        "type": "PLAIN",
        "hash": null
      },
      "asset": "employee@example.com"
    }
  ]
}
```
