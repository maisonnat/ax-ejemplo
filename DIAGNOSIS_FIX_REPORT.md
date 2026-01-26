# Reporte de Diagnóstico y Corrección: Contabilización de Incidentes en Risk Score

**Fecha:** 26 de Enero, 2026
**Cliente:** SRCL
**Asunto:** Discrepancia en conteo de incidentes (SURA-AFORE vs Total Tenant)

---

## 1. Resumen Ejecutivo

Se identificó que el cálculo del **Risk Score v3.0** mostraba un volumen de incidentes mayor al esperado para la marca **SURA-AFORE (AFSR)**.

El diagnóstico confirmó que la API de estadísticas de Axur (`/stats`) contabiliza incidentes a nivel **Tenant (SRCL)** completo, sumando incidentes de otras marcas activas (como Suramericana `SRAS` y Prosur `PRSR36`) al reporte de AFORE.

**Estado Actual:** ✅ **CORREGIDO**
La herramienta ha sido actualizada para filtrar incidentes estrictamente por el **Asset ID** (ej. `AFSR`), asegurando que el Risk Score refleje únicamente la realidad de la marca analizada.

---

## 2. Diagnóstico Técnico

### El Problema
El script original utilizaba el siguiente endpoint para el KRI de Volumen:

```http
GET /tickets-api/stats/incident/count/ticket-types?customer=SRCL
```

Este endpoint retorna la suma total de incidentes para el cliente `SRCL`. Al tener este cliente múltiples marcas configuradas, el resultado agregaba:

*   **AFSR** (SURA-AFORE): ~5% de los incidentes
*   **SRAS** (Suramericana): ~75% de los incidentes
*   **PRSR36** (Prosur): ~11% de los incidentes

Esto resultaba en "falsos positivos" para el reporte de AFORE, inflando el riesgo calculado.

### Evidencia (Debug)
Se ejecutó un análisis detallado de los tickets del 25-26 de Enero, encontrando la siguiente distribución real para `SRCL`:

| Asset / Marca | Conteo | % del Total |
|:---|:---:|:---|
| **SRAS** | 75 | 75% |
| **PRSR36** | 11 | 11% |
| **AFSR (Objetivo)** | **5** | **5%** |
| AFINP | 4 | 4% |
| Otros | 5 | 5% |

El reporte anterior mostraba la suma total (~100), cuando para AFORE debió mostrar solo 5.

---

## 3. Solución Implementada

Se modificó la lógica de recolección de datos (`mainTest.py`) para abandonar el uso de estadísticas agregadas y pasar a un **conteo exacto basado en tickets**.

### Cambios en el Algoritmo:

1.  **Cambio de Fuente de Datos:**
    *   **Antes:** Usaba `/stats` (Pre-calculado por Axur, nivel Tenant).
    *   **Ahora:** Usa `/tickets` (Lista detallada de cada incidente).

2.  **Filtrado por Asset:**
    *   El script ahora descarga el detalle de los incidentes y verifica el campo `detection.assets`.
    *   **Solo** si el ticket contiene el Asset seleccionado (ej. `AFSR`), se suma al Risk Score.

3.  **Selección de Marca:**
    *   Al ejecutar la herramienta, ahora se permite seleccionar explícitamente qué marca (Asset) se desea auditar.

### Beneficio
*   **Precisión Total:** El Score ahora aísla perfectamente los riesgos de SURA-AFORE sin "ruido" de otras subsidiarias.
*   **Transparencia:** Se puede auditar exactamente qué tickets compusieron el puntaje.

---

## 4. Instrucciones de Uso

Para ejecutar el análisis corregido:

1. Iniciar el script:
   ```bash
   python mainTest.py
   ```
2. Seleccionar **[1] RISK SCORE v3.0**.
3. El sistema preguntará:
   ```
   ¿Desea filtrar por una Marca/Asset específico? [S/n]: s
   ```
4. Seleccionar la marca de la lista (ej. `AFSR`).

---

## 5. Discrepancia de Tickets Faltantes (Actualización)

### Síntoma
Algunos tickets específicos (ej. `fudmz0`, `412xd5`) no aparecían en el análisis, a pesar de estar dentro del rango de fechas seleccionado.

### Causa Raíz
1. **Límite de API (PageSize):** El script solicitaba `pageSize=500` por defecto. La API de Axur tiene un límite estricto de **200**. Esto provocaba que la API devolviera un error HTTP 400, resultando en 0 tickets recuperados en ciertas consultas silenciosas.
2. **Falta de Paginación:** Incluso con un `pageSize` válido, si el volumen de tickets superaba los 200 en el periodo seleccionado (ej. últimos 30 días), el script solo obtenía los primeros 200. Los tickets más antiguos (o desplazados por el ordenamiento) quedaban fuera.

### Solución Implementada
- **Corrección de PageSize:** Se ajustó el parámetro a `200` (máximo permitido).
- **Implementación de Paginación:** Se reescribió la función `get_incidents_for_period` para iterar automáticamente sobre todas las páginas de resultados hasta recuperar la totalidad de los tickets del periodo.
- **Soporte de Rango de Fecha Preciso:** Se añadió el filtro `le:` para fecha fin y se incluyó la hora (T00:00:00 - T23:59:59) para evitar truncar datos del último día.

### Resultado
El script ahora recupera la totalidad de los tickets disponibles en Axur para el rango y marca seleccionados, encontrando exitosamente tickets críticos como `fudmz0` y `412xd5` que previamente eran excluidos por la falta de precisión horaria.

---

## 6. Nueva Funcionalidad: Filtro de Incidentes Activos

### Contexto
Se observó que el script reportaba un volumen de incidentes mayor al visible en la vista por defecto del portal.
*   **Causa:** El script contabilizaba histórico completo (Incidents + Discarded).
*   **Portal:** Muestra por defecto "Pendientes" o "Confirmados".

### Solución
Se implementó una nueva opción interactiva en el menú:
```
  ¿Excluir tickets descartados/falsos positivos? (Mostrar solo Amenazas Activas)
  [S/n]:
```
*   **Sí (S):** Excluye tickets con `resolution: discarded`. Alinea el conteo con amenazas reales/activas.
*   **No (n):** Muestra volumen total de tráfico/intentos (útil para medir intensidad de ataque).

Esta opción permite al analista decidir entre "Limpieza de Ruido" (para operación) y "Volumen Total" (para métricas de amenaza).

