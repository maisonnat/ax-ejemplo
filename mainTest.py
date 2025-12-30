import requests
import json
import time
import sys
import os
from datetime import datetime, timedelta

# Fix encoding for Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

# =============================================================================
# CARGAR CONFIGURACIÓN DESDE config.json
# =============================================================================

def load_config():
    """Carga la configuración desde config.json"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        print("⚠️  Archivo config.json no encontrado. Usando valores por defecto.")
        return {
            "api_key": "YOUR_API_KEY_HERE",
            "customer_id": "YOUR_CUSTOMER_ID",
            "base_url": "https://api.axur.com/gateway/1.0/api",
            "days_range": 30
        }

CONFIG = load_config()

# =============================================================================
# CONFIGURACIÓN GLOBAL (desde config.json)
# =============================================================================

API_KEY = CONFIG.get("api_key", "YOUR_API_KEY_HERE")
CUSTOMER_ID = CONFIG.get("customer_id", "YOUR_CUSTOMER_ID")
BASE_URL = CONFIG.get("base_url", "https://api.axur.com/gateway/1.0/api")
DAYS_RANGE = CONFIG.get("days_range", 30)

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Rango de fechas (desde config o 30 días por defecto)
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=DAYS_RANGE)
FMT_DATE = "%Y-%m-%dT%H:%M:%S"


# =============================================================================
# OBTENER DOMINIOS Y BRANDS DEL CLIENTE DESDE LA API
# =============================================================================

def get_customer_assets():
    """
    Obtiene las marcas (Brands) y dominios del cliente, creando un mapeo
    entre cada dominio y su marca asociada.
    
    Relación: Brand.properties["OFFICIAL_WEBSITE"] contiene el dominio asociado.
    
    Returns:
        tuple: (brands_list, domain_to_brand_map)
        - brands_list: Lista de dicts {name, key, official_website, size}
        - domain_to_brand_map: Dict {domain_name: brand_name}
    """
    endpoint = f"{BASE_URL}/customers/customers"
    brands = []
    domains = []
    domain_to_brand = {}
    
    try:
        response = requests.get(endpoint, headers=HEADERS)
        if response.status_code == 200:
            customers = response.json()
            
            for customer in customers:
                if customer.get("key") == CUSTOMER_ID:
                    assets = customer.get("assets", [])
                    
                    # 1. Extraer Brands y Domains
                    for asset in assets:
                        category = asset.get("category")
                        
                        if category == "BRAND" and asset.get("active", True):
                            brand_info = {
                                "name": asset.get("name"),
                                "key": asset.get("key"),
                                "official_website": None,
                                "size": None
                            }
                            for prop in asset.get("properties", []):
                                if prop.get("name") == "OFFICIAL_WEBSITE":
                                    brand_info["official_website"] = prop.get("value", "")
                                elif prop.get("name") == "BRAND_SIZE":
                                    brand_info["size"] = prop.get("value")
                            brands.append(brand_info)
                            
                        elif category == "DOMAIN" and asset.get("active", True):
                            domain_name = asset.get("name")
                            if domain_name:
                                domains.append(domain_name)
                    
                    # 2. Crear mapeo Domain -> Brand
                    for domain in domains:
                        matched_brand = None
                        domain_lower = domain.lower()
                        domain_base = domain_lower.split(".")[0]  # e.g. "proteccion" from "proteccion.com"
                        
                        for brand in brands:
                            official_site = (brand.get("official_website") or "").lower()
                            
                            # Match exacto del dominio en URL
                            if domain_lower in official_site:
                                matched_brand = brand["name"]
                                break
                            
                            # Match por base del dominio (ej: "proteccion" en "proteccion.com")
                            if domain_base in official_site and len(domain_base) > 3:
                                matched_brand = brand["name"]
                                break
                        
                        domain_to_brand[domain] = matched_brand
                    
                    break
                    
    except Exception as e:
        print(f"  [Error] No se pudieron obtener assets: {e}")
    
    return brands, domain_to_brand


def get_customer_domains():
    """
    Función de compatibilidad. Retorna solo la lista de dominios.
    """
    _, domain_map = get_customer_assets()
    return list(domain_map.keys())


# =============================================================================
# ÍNDICE DE HIGIENE (30%) - Basado en Exposure API
# =============================================================================

def get_credential_exposure_score():
    """
    Calcula el índice de higiene basado en:
    1. Formato de la fuga (STEALER LOG = crítico)
    2. Tipo de contraseña (PLAIN = máximo riesgo)
    
    Fuente: /exposure-api/credentials
    """
    endpoint = f"{BASE_URL}/exposure-api/credentials"
    
    params = {
        "status": "NEW,IN_TREATMENT",
        "created": f"ge:{START_DATE.strftime('%Y-%m-%d')}",
        "customer": CUSTOMER_ID,
        "pageSize": 100,
        "fields": "id,status,password.type,leak.format"
    }
    
    hygiene_penalty = 0
    stealer_count = 0
    plain_password_count = 0
    hashed_password_count = 0
    
    try:
        response = requests.get(endpoint, headers=HEADERS, params=params)
        if response.status_code == 200:
            data = response.json()
            detections = data.get("detections", [])
            
            for detection in detections:
                leak_format = detection.get("leak.format", "")
                password_type = detection.get("password.type", "UNKNOWN")
                
                if leak_format == "STEALER LOG":
                    hygiene_penalty += 50
                    stealer_count += 1
                elif leak_format == "COMBOLIST":
                    hygiene_penalty += 10
                else:
                    hygiene_penalty += 5
                
                if password_type == "PLAIN":
                    hygiene_penalty += 30
                    plain_password_count += 1
                elif password_type in ["BCRYPT", "SHA256", "SHA512", "PBKDF2"]:
                    hygiene_penalty += 6
                    hashed_password_count += 1
                else:
                    hygiene_penalty += 15
            
            print(f"  [Higiene] Stealer Logs detectados: {stealer_count}")
            print(f"  [Higiene] Contraseñas en texto plano: {plain_password_count}")
            print(f"  [Higiene] Contraseñas hasheadas: {hashed_password_count}")
                    
    except Exception as e:
        print(f"Error obteniendo exposiciones de credenciales: {e}")
    
    return hygiene_penalty


# =============================================================================
# ÍNDICE DE RESPUESTA (30%) - Basado en Takedown Uptime
# =============================================================================

def get_response_efficiency_score():
    endpoint = f"{BASE_URL}/tickets-api/stats/takedown/uptime"
    params = {
        "customer": CUSTOMER_ID,
        "from": START_DATE.strftime(FMT_DATE),
        "to": END_DATE.strftime(FMT_DATE)
    }
    
    response_score = 300
    
    try:
        response = requests.get(endpoint, headers=HEADERS, params=params)
        if response.status_code == 200:
            uptime = response.json().get("uptime", {})
            
            total_resolved = sum([
                uptime.get("lessThan1Day", 0),
                uptime.get("upTo2Days", 0),
                uptime.get("upTo5Days", 0),
                uptime.get("upTo10Days", 0),
                uptime.get("upTo15Days", 0),
                uptime.get("upTo30Days", 0),
                uptime.get("upTo60Days", 0),
                uptime.get("over60Days", 0)
            ])
            
            if total_resolved > 0:
                fast_resolution = uptime.get("lessThan1Day", 0) / total_resolved
                slow_resolution = (
                    uptime.get("upTo15Days", 0) + 
                    uptime.get("upTo30Days", 0) + 
                    uptime.get("upTo60Days", 0) + 
                    uptime.get("over60Days", 0)
                ) / total_resolved
                
                response_score = int(300 * (1 - slow_resolution))
                
                print(f"  [Respuesta] Resueltas < 1 día: {uptime.get('lessThan1Day', 0)}")
                print(f"  [Respuesta] Resueltas > 10 días: {uptime.get('upTo15Days', 0) + uptime.get('upTo30Days', 0) + uptime.get('upTo60Days', 0) + uptime.get('over60Days', 0)}")
                print(f"  [Respuesta] Ratio respuesta rápida: {fast_resolution:.1%}")
            
    except Exception as e:
        print(f"Error obteniendo uptime de takedown: {e}")
        
    return response_score


# =============================================================================
# VOLUMEN DE AMENAZAS (20%) - Basado en ticket-types
# =============================================================================

def get_incident_volume_score():
    endpoint = f"{BASE_URL}/tickets-api/stats/incident/count/ticket-types"
    params = {
        "customer": CUSTOMER_ID,
        "from": START_DATE.strftime(FMT_DATE),
        "to": END_DATE.strftime(FMT_DATE),
        "ticketTypes": "phishing,malware,ransomware-attack,fake-social-media-profile,infostealer-credential,data-sale-message"
    }
    
    volume_score = 200
    total_incidents = 0
    
    try:
        response = requests.get(endpoint, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        
        for item in data.get("totalByTicketType", []):
            count = item.get("totalOnPeriod", 0)
            t_type = item.get("type")
            total_incidents += count
            
            if t_type in ["ransomware-attack", "malware", "infostealer-credential"]:
                volume_score -= (count * 15)
            elif t_type in ["phishing", "data-sale-message"]:
                volume_score -= (count * 8)
            else:
                volume_score -= (count * 3)
        
        print(f"  [Volumen] Total incidentes en período: {total_incidents}")
                
    except Exception as e:
        print(f"Error obteniendo incidentes: {e}")
        
    return max(0, volume_score)


# =============================================================================
# ÍNDICE DE DAÑO REAL (20%) - Basado en Web Complaints
# =============================================================================

def get_real_damage_score():
    damage_score = 200
    
    endpoint = f"{BASE_URL}/web-complaints/results"
    params = {
        "initialDate": START_DATE.strftime("%Y-%m-%d"),
        "finalDate": END_DATE.strftime("%Y-%m-%d"),
        "order": "desc",
        "timezone": "-03:00",
        "page": 1,
        "pageSize": 200
    }
    
    try:
        response = requests.get(endpoint, headers=HEADERS, params=params)
        if response.status_code == 200:
            data = response.json()
            total_complaints = data.get("totalElements", 0)
            damage_penalty = total_complaints * 10
            damage_score -= damage_penalty
            print(f"  [Daño Real] Quejas web registradas: {total_complaints}")
        elif response.status_code == 401:
            print("  [Daño Real] Sin acceso a Web Complaints API")
        else:
            print(f"  [Daño Real] Web Complaints: status {response.status_code}")
            
    except Exception as e:
        print(f"Error obteniendo web complaints: {e}")
    
    return max(0, damage_score)


# =============================================================================
# CÁLCULO FINAL DEL RISK SCORE
# =============================================================================

def calculate_risk_score():
    print(f"\n{'='*60}")
    print(f"  PUNTUACIÓN DE POSTURA DE RIESGO v2.0 - {CUSTOMER_ID}")
    print(f"{'='*60}")
    print(f"  Período: {START_DATE.strftime('%Y-%m-%d')} a {END_DATE.strftime('%Y-%m-%d')}")
    print(f"{'='*60}\n")
    
    print("[1/4] Calculando Índice de Higiene (Exposure API)...")
    hygiene_penalty = get_credential_exposure_score()
    hygiene_score = max(0, 300 - hygiene_penalty)
    print(f"      → Puntuación: {hygiene_score}/300\n")
    
    print("[2/4] Calculando Índice de Respuesta (Takedown Uptime)...")
    response_score = get_response_efficiency_score()
    print(f"      → Puntuación: {response_score}/300\n")
    
    print("[3/4] Calculando Volumen de Amenazas (Ticket Types)...")
    volume_score = get_incident_volume_score()
    print(f"      → Puntuación: {volume_score}/200\n")
    
    print("[4/4] Calculando Índice de Daño Real (Web Complaints)...")
    damage_score = get_real_damage_score()
    print(f"      → Puntuación: {damage_score}/200\n")
    
    final_score = hygiene_score + response_score + volume_score + damage_score
    final_score = max(0, min(1000, final_score))
    
    print(f"{'='*60}")
    print(f"  DESGLOSE DE PUNTUACIÓN:")
    print(f"{'='*60}")
    print(f"  • Índice de Higiene:      {hygiene_score:>4}/300  ({hygiene_score/3:.1f}%)")
    print(f"  • Índice de Respuesta:    {response_score:>4}/300  ({response_score/3:.1f}%)")
    print(f"  • Volumen de Amenazas:    {volume_score:>4}/200  ({volume_score/2:.1f}%)")
    print(f"  • Índice de Daño Real:    {damage_score:>4}/200  ({damage_score/2:.1f}%)")
    print(f"{'='*60}")
    print(f"\n  ╔════════════════════════════════════════════════════════╗")
    print(f"  ║  PUNTUACIÓN FINAL DE RIESGO: {final_score:>4}/1000               ║")
    print(f"  ╚════════════════════════════════════════════════════════╝\n")
    
    if final_score >= 800:
        print("  ✅ Estado: EXCELENTE (Bajo Riesgo)")
    elif final_score >= 600:
        print("  ⚠️  Estado: BUENO (Riesgo Moderado)")
    elif final_score >= 400:
        print("  🔶 Estado: ALERTA (Riesgo Medio-Alto)")
    else:
        print("  🔴 Estado: CRÍTICO (Alto Riesgo)")
    
    print()
    return final_score


# =============================================================================
# RISK SCORE v3.0 (KRI Model)
# =============================================================================

# Pesos de incidentes por tipo de amenaza
INCIDENT_WEIGHTS = {
    "ransomware-attack": 100,
    "malware": 80,
    "infostealer-credential": 80,
    "phishing": 50,
    "data-sale-message": 40,
    "data-sale-website": 40,
    "corporate-credential-leak": 35,
    "database-exposure": 35,
    "fake-social-media-profile": 20,
    "fraudulent-brand-use": 20,
    "similar-domain-name": 15,
    "fake-mobile-app": 30,
    "paid-search": 10,
}

def get_weighted_incidents():
    """
    KRI 1: Volumen ponderado de incidentes por gravedad.
    Endpoint: /tickets-api/stats/incident/count/ticket-types
    """
    endpoint = f"{BASE_URL}/tickets-api/stats/incident/count/ticket-types"
    params = {
        "customer": CUSTOMER_ID,
        "from": START_DATE.strftime(FMT_DATE),
        "to": END_DATE.strftime(FMT_DATE)
    }
    
    weighted_score = 0
    total_incidents = 0
    breakdown = {}
    
    try:
        response = requests.get(endpoint, headers=HEADERS, params=params)
        if response.status_code == 200:
            data = response.json()
            for item in data.get("totalByTicketType", []):
                t_type = item.get("type", "")
                count = item.get("totalOnPeriod", 0)
                weight = INCIDENT_WEIGHTS.get(t_type, 10)
                
                weighted_score += count * weight
                total_incidents += count
                if count > 0:
                    breakdown[t_type] = {"count": count, "weight": weight, "score": count * weight}
                    
    except Exception as e:
        print(f"  [Error] Incidentes: {e}")
    
    return weighted_score, total_incidents, breakdown


def get_market_benchmark():
    """
    KRI 2: Comparativa con la MEDIANA del segmento de mercado del cliente.
    Endpoint: /tickets-api/stats/incident/customer/market-segment/median
    
    La API devuelve 13 meses de datos con estructura:
    {
        "marketSegment": "TECHNOLOGY",
        "medians": [{"total": 42, "referenceMonth": "2024-11"}, ...]
    }
    """
    endpoint = f"{BASE_URL}/tickets-api/stats/incident/customer/market-segment/median"
    params = {
        "customer": CUSTOMER_ID,
        "to": END_DATE.strftime("%Y-%m-%d"),
        "timezone": "-03:00"
    }
    
    market_segment = "UNKNOWN"
    sector_median = 0
    reference_month = ""
    
    try:
        response = requests.get(endpoint, headers=HEADERS, params=params)
        if response.status_code == 200:
            data = response.json()
            market_segment = data.get("marketSegment", "UNKNOWN")
            
            # Obtener array de medianas mensuales
            # La respuesta puede usar "medians" o "mean" dependiendo del endpoint
            monthly_data = data.get("medians", data.get("mean", []))
            
            if monthly_data and isinstance(monthly_data, list):
                # Tomar el último mes (más reciente)
                last_month = monthly_data[-1]
                sector_median = last_month.get("total", 0)
                reference_month = last_month.get("referenceMonth", "")
        elif response.status_code == 403:
            pass  # Sin acceso
        else:
            pass
                
    except Exception as e:
        print(f"  [Error] Benchmark: {e}")
    
    return market_segment, sector_median, reference_month


def get_stealer_log_count():
    """
    KRI 3: Conteo de credenciales de Stealer Logs (malware activo).
    Endpoint: /exposure-api/credentials con leak.format=STEALER LOG
    """
    endpoint = f"{BASE_URL}/exposure-api/credentials"
    params = {
        "customer": CUSTOMER_ID,
        "status": "NEW,IN_TREATMENT",
        "created": f"ge:{START_DATE.strftime('%Y-%m-%d')}",
        "pageSize": 1  # Solo necesitamos el total
    }
    
    stealer_count = 0
    plain_password_count = 0
    
    try:
        # Primero: Stealer Logs
        response = requests.get(endpoint, headers=HEADERS, params=params)
        if response.status_code == 200:
            # La API no permite filtrar por leak.format directamente,
            # así que obtenemos una muestra y contamos
            params["pageSize"] = 100
            response = requests.get(endpoint, headers=HEADERS, params=params)
            if response.status_code == 200:
                detections = response.json().get("detections", [])
                for d in detections:
                    if d.get("leak.format") == "STEALER LOG":
                        stealer_count += 1
                    if d.get("password.type") == "PLAIN":
                        plain_password_count += 1
                        
    except Exception as e:
        print(f"  [Error] Stealer logs: {e}")
    
    return stealer_count, plain_password_count


def get_operational_efficiency():
    """
    KRI 4: Eficiencia operativa basada en tiempos de resolución.
    Endpoint: /tickets-api/stats/takedown/uptime
    """
    endpoint = f"{BASE_URL}/tickets-api/stats/takedown/uptime"
    params = {
        "customer": CUSTOMER_ID,
        "from": START_DATE.strftime(FMT_DATE),
        "to": END_DATE.strftime(FMT_DATE)
    }
    
    uptime_data = {}
    slow_count = 0
    total_count = 0
    
    try:
        response = requests.get(endpoint, headers=HEADERS, params=params)
        if response.status_code == 200:
            uptime_data = response.json().get("uptime", {})
            
            total_count = sum([
                uptime_data.get("lessThan1Day", 0),
                uptime_data.get("upTo2Days", 0),
                uptime_data.get("upTo5Days", 0),
                uptime_data.get("upTo10Days", 0),
                uptime_data.get("upTo15Days", 0),
                uptime_data.get("upTo30Days", 0),
                uptime_data.get("upTo60Days", 0),
                uptime_data.get("over60Days", 0)
            ])
            
            slow_count = (
                uptime_data.get("upTo30Days", 0) +
                uptime_data.get("upTo60Days", 0) +
                uptime_data.get("over60Days", 0)
            )
            
    except Exception as e:
        print(f"  [Error] Uptime: {e}")
    
    return uptime_data, slow_count, total_count


def get_web_complaints_count():
    """
    KRI 5: Conteo de quejas web (riesgo reputacional).
    Endpoint: /web-complaints/results
    """
    endpoint = f"{BASE_URL}/web-complaints/results"
    params = {
        "initialDate": START_DATE.strftime("%Y-%m-%d"),
        "finalDate": END_DATE.strftime("%Y-%m-%d"),
        "page": 1,
        "pageSize": 1
    }
    
    complaints_count = 0
    
    try:
        response = requests.get(endpoint, headers=HEADERS, params=params)
        if response.status_code == 200:
            complaints_count = response.json().get("totalElements", 0)
    except:
        pass
    
    return complaints_count


def calculate_risk_score_v3():
    """
    Risk Score v3.0 - Modelo KRI (Key Risk Indicators)
    
    Fórmula: Score = Base × (1 + StealerFactor) × (1 + SlowFactor) × (1 + ComplaintsFactor)
    
    Donde Base = min(1000, WeightedIncidents / MarketRatio)
    """
    print(f"\n{'='*65}")
    print(f"  ╔═══════════════════════════════════════════════════════════╗")
    print(f"  ║  RISK SCORE v3.0 (Modelo KRI) - {CUSTOMER_ID:^20}       ║")
    print(f"  ╚═══════════════════════════════════════════════════════════╝")
    print(f"  Período: {START_DATE.strftime('%Y-%m-%d')} a {END_DATE.strftime('%Y-%m-%d')}")
    print(f"{'='*65}\n")
    
    # --- KRI 1: Weighted Incidents ---
    print("[1/5] Analizando Volumen Ponderado de Incidentes...")
    weighted_score, total_incidents, breakdown = get_weighted_incidents()
    
    top_threats = sorted(breakdown.items(), key=lambda x: x[1]["score"], reverse=True)[:3]
    if top_threats:
        print(f"      Top 3 amenazas:")
        for t_type, info in top_threats:
            print(f"        • {t_type}: {info['count']} × {info['weight']} = {info['score']} pts")
    print(f"      → Volumen ponderado: {weighted_score} pts ({total_incidents} incidentes)\n")
    
    # --- KRI 2: Market Benchmark ---
    print("[2/5] Obteniendo Benchmark del Sector...")
    market_segment, sector_median, reference_month = get_market_benchmark()
    
    if sector_median > 0:
        ratio = total_incidents / sector_median
        ratio_text = f"{ratio:.2f}x"
        if ratio < 0.5:
            benchmark_status = "🟢 Excelente (mejor que pares)"
        elif ratio < 1.0:
            benchmark_status = "🟡 Bueno (bajo la mediana)"
        elif ratio < 2.0:
            benchmark_status = "🟠 Alerta (sobre la mediana)"
        else:
            benchmark_status = "🔴 Crítico (muy sobre la mediana)"
    else:
        ratio = 1.0
        ratio_text = "N/A"
        benchmark_status = "⚪ Sin datos de benchmark"
    
    print(f"      Segmento: {market_segment}")
    print(f"      Mediana del sector: {sector_median:.0f} incidentes/mes ({reference_month})")
    print(f"      Tu incidentes: {total_incidents} | Ratio: {ratio_text}")
    print(f"      → {benchmark_status}\n")
    
    # --- KRI 3: Stealer Logs (Critical) ---
    print("[3/5] Detectando Stealer Logs (Malware Activo)...")
    stealer_count, plain_count = get_stealer_log_count()
    
    if stealer_count == 0:
        stealer_factor = 0
        stealer_status = "🟢 Sin infecciones detectadas"
    elif stealer_count <= 5:
        stealer_factor = 0.2
        stealer_status = f"🟠 {stealer_count} dispositivos comprometidos (+20%)"
    elif stealer_count <= 20:
        stealer_factor = 0.5
        stealer_status = f"🔴 {stealer_count} dispositivos comprometidos (+50%)"
    else:
        stealer_factor = 1.0
        stealer_status = f"🔴🔴 {stealer_count} dispositivos comprometidos (+100%)"
    
    print(f"      Stealer Logs: {stealer_count}")
    print(f"      Contraseñas en texto plano: {plain_count}")
    print(f"      → Factor: {stealer_status}\n")
    
    # --- KRI 4: Operational Efficiency ---
    print("[4/5] Evaluando Eficiencia Operativa...")
    uptime_data, slow_count, total_count = get_operational_efficiency()
    
    if total_count > 0:
        efficiency_pct = ((total_count - slow_count) / total_count) * 100
        slow_factor = slow_count / total_count * 0.5  # Max 50% penalty
        fast_count = uptime_data.get("lessThan1Day", 0) + uptime_data.get("upTo2Days", 0)
        
        if efficiency_pct >= 90:
            efficiency_status = "🟢 Excelente"
        elif efficiency_pct >= 70:
            efficiency_status = "🟡 Buena"
        else:
            efficiency_status = "🔴 Deficiente"
    else:
        efficiency_pct = 100
        slow_factor = 0
        fast_count = 0
        efficiency_status = "⚪ Sin datos"
    
    print(f"      Resueltos rápido (<2 días): {fast_count}")
    print(f"      Resueltos lento (>30 días): {slow_count}")
    print(f"      → Eficiencia: {efficiency_pct:.0f}% - {efficiency_status}\n")
    
    # --- KRI 5: Impacto Reputacional ---
    print("[5/5] Evaluando Impacto Reputacional...")
    reputational_count = get_web_complaints_count()
    
    if reputational_count == 0:
        reputational_factor = 0
        reputational_status = "🟢 Sin reportes de víctimas"
    elif reputational_count <= 10:
        reputational_factor = 0.1
        reputational_status = f"🟡 {reputational_count} reportes (+10%)"
    elif reputational_count <= 50:
        reputational_factor = 0.3
        reputational_status = f"🟠 {reputational_count} reportes (+30%)"
    else:
        reputational_factor = 0.5
        reputational_status = f"🔴 {reputational_count} reportes (+50%)"
    
    print(f"      → Impacto: {reputational_status}\n")
    
    # --- CÁLCULO FINAL ---
    # Base score: weighted incidents normalized by market ratio
    if ratio > 0:
        base_score = min(500, weighted_score / max(ratio, 0.5))
    else:
        base_score = min(500, weighted_score)
    
    # Aplicar factores multiplicadores (penalizan el score)
    total_penalty_factor = (1 + stealer_factor) * (1 + slow_factor) * (1 + reputational_factor)
    
    # Score final: 1000 - (base_score * penalty_factor)
    # Más incidentes = más base_score = menos puntos finales
    final_score = max(0, min(1000, 1000 - (base_score * total_penalty_factor)))
    final_score = int(final_score)
    
    # Determinar estado
    if final_score >= 800:
        estado = "🟢 EXCELENTE"
        estado_desc = "Postura de seguridad sólida"
    elif final_score >= 600:
        estado = "🟡 BUENO"
        estado_desc = "Riesgo moderado, monitorear"
    elif final_score >= 400:
        estado = "🟠 ALERTA"
        estado_desc = "Acciones preventivas recomendadas"
    else:
        estado = "🔴 CRÍTICO"
        estado_desc = "Requiere atención inmediata"
    
    # Mostrar resultado
    print(f"{'='*65}")
    print(f"  RESUMEN DE INDICADORES:")
    print(f"{'='*65}")
    print(f"  • Volumen Ponderado:    {weighted_score:>6} pts  ({total_incidents} incidentes)")
    print(f"  • Benchmark Sector:     {ratio_text:>6}     ({market_segment})")
    print(f"  • Stealer Logs:         {stealer_count:>6}      (Factor: +{stealer_factor*100:.0f}%)")
    print(f"  • Eficiencia Ops:       {efficiency_pct:>5.0f}%     ({slow_count} lentos)")
    print(f"  • Impacto Reputacional: {reputational_count:>6}      (Factor: +{reputational_factor*100:.0f}%)")
    print(f"{'='*65}")
    
    print(f"\n  ╔═══════════════════════════════════════════════════════════╗")
    print(f"  ║  SCORE FINAL:  {final_score:>4}/1000   {estado:^25}       ║")
    print(f"  ╠═══════════════════════════════════════════════════════════╣")
    print(f"  ║  {estado_desc:^55}      ║")
    print(f"  ╚═══════════════════════════════════════════════════════════╝\n")
    
    return final_score


# =============================================================================
# CONSULTA DE CREDENCIALES DETECTADAS (Exposure API - SIN consumir créditos)
# =============================================================================

def get_detected_credentials(domain_filter=None, days_back=7, show_details=True):
    """
    Consulta credenciales YA DETECTADAS por Axur para el cliente.
    
    DIFERENCIA CON THREAT HUNTING:
    - Threat Hunting: Busca en Deep Web cruda. CONSUME créditos.
    - Exposure API: Consulta incidentes YA confirmados. NO consume créditos.
    """
    endpoint = f"{BASE_URL}/exposure-api/credentials"
    
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    params = {
        "customer": CUSTOMER_ID,
        "created": f"ge:{start_date}",
        "status": "NEW,IN_TREATMENT",
        "pageSize": 50,
        "sortBy": "created",
        "order": "desc"
    }
    
    if domain_filter:
        params["user"] = f"contains:{domain_filter}"
    
    print(f"\n{'='*60}")
    print(f"  CREDENCIALES DETECTADAS - Exposure API")
    print(f"{'='*60}")
    print(f"  Cliente: {CUSTOMER_ID}")
    print(f"  Período: últimos {days_back} días (desde {start_date})")
    if domain_filter:
        print(f"  Filtro dominio: {domain_filter}")
    print(f"{'='*60}\n")
    
    try:
        response = requests.get(endpoint, headers=HEADERS, params=params)
        
        if response.status_code == 200:
            data = response.json()
            detections = data.get("detections", [])
            total = data.get("pageable", {}).get("total", 0)
            
            print(f"  🔍 Total credenciales detectadas: {total}")
            
            if detections and show_details:
                print(f"\n  --- Detalle de credenciales ---\n")
                
                by_type = {"PLAIN": 0, "HASHED": 0}
                by_format = {"STEALER LOG": 0, "COMBOLIST": 0, "OTHER": 0}
                
                for i, item in enumerate(detections[:10]):
                    email = item.get("user", "N/A")
                    pwd_type = item.get("password.type", "UNKNOWN")
                    leak_format = item.get("leak.format", "UNKNOWN")
                    source = item.get("source.name", item.get("leak.displayName", "Fuente desconocida"))
                    created = item.get("created", "N/A")
                    
                    if pwd_type == "PLAIN":
                        by_type["PLAIN"] += 1
                    else:
                        by_type["HASHED"] += 1
                    
                    if leak_format == "STEALER LOG":
                        by_format["STEALER LOG"] += 1
                    elif leak_format == "COMBOLIST":
                        by_format["COMBOLIST"] += 1
                    else:
                        by_format["OTHER"] += 1
                    
                    print(f"  [{i+1}] {email}")
                    print(f"      Tipo: {pwd_type} | Formato: {leak_format}")
                    print(f"      Fuente: {source}")
                    print(f"      Detectada: {created}\n")
                
                if total > 10:
                    print(f"  ... y {total - 10} credenciales más.\n")
                
                print(f"  {'='*50}")
                print(f"  RESUMEN:")
                print(f"  {'='*50}")
                print(f"  • Contraseñas en TEXTO PLANO: {by_type['PLAIN']} (🔴 Crítico)")
                print(f"  • Contraseñas HASHEADAS:      {by_type['HASHED']}")
                print(f"  • Stealer Logs (malware):     {by_format['STEALER LOG']} (🔴 Máquinas infectadas)")
                print(f"  • Combolists:                 {by_format['COMBOLIST']}")
            
            if detections:
                output_file = f"credentials_{CUSTOMER_ID}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(detections, f, indent=2, ensure_ascii=False)
                    print(f"\n  📁 Exportado a: {output_file}")
                except:
                    pass
            
            return detections
            
        elif response.status_code == 403:
            print("  [!] Sin acceso a Exposure API para este cliente.")
        else:
            print(f"  [!] Error: {response.status_code}")
            
    except Exception as e:
        print(f"  [Error] {e}")
    
    return []


# =============================================================================
# EJECUCIÓN PRINCIPAL
# =============================================================================

def main():
    # 1. Calcular Risk Score v3.0 (KRI Model)
    risk_score = calculate_risk_score_v3()
    
    # 2. Obtener Brands y Dominios del cliente
    print(f"\n{'='*60}")
    print("  Obteniendo Brands y Dominios del cliente...")
    print(f"{'='*60}")
    
    brands, domain_to_brand = get_customer_assets()
    
    if brands:
        print(f"\n  ✅ Se encontraron {len(brands)} marcas (Brands):\n")
        
        # Agrupar dominios por marca
        brand_domains = {brand["name"]: [] for brand in brands}
        unassigned_domains = []
        
        for domain, brand_name in domain_to_brand.items():
            if brand_name and brand_name in brand_domains:
                brand_domains[brand_name].append(domain)
            else:
                unassigned_domains.append(domain)
        
        # Mostrar cada marca con sus dominios
        for i, brand in enumerate(brands, 1):
            brand_name = brand["name"]
            website = brand.get("official_website") or "(sin sitio)"
            size = brand.get("size") or ""
            associated_domains = brand_domains.get(brand_name, [])
            
            print(f"  [{i}] {brand_name} ({size})")
            print(f"      Sitio oficial: {website}")
            if associated_domains:
                print(f"      Dominios asociados:")
                for d in associated_domains:
                    print(f"        • {d}")
            print()
        
        if unassigned_domains:
            print(f"  --- Dominios sin marca asignada ({len(unassigned_domains)}) ---")
            for d in unassigned_domains[:10]:
                print(f"      • {d}")
            if len(unassigned_domains) > 10:
                print(f"      ... y {len(unassigned_domains) - 10} más.")
    else:
        print("  ⚠️  No se encontraron marcas configuradas para este cliente.")
    
    # 3. Consultar credenciales detectadas (Exposure API - SIN consumir créditos)
    print(f"\n{'='*60}")
    print("  ¿Consultar credenciales detectadas?")
    print("  (Usa Exposure API - NO consume créditos)")
    print(f"{'='*60}")
    
    all_domains = list(domain_to_brand.keys())
    
    try:
        resp = input("\n  Consultar credenciales? (s/n): ").strip().lower()
        if resp in ['s', 'si', 'y', 'yes']:
            if all_domains:
                # Mostrar opciones: por marca o por dominio
                print(f"\n  Selecciona una opción:")
                print(f"      [0] Sin filtro (mostrar TODAS sin restricción)")
                print(f"      [A] TODAS pero solo dominios del cliente")
                print(f"      [B] Filtrar por MARCA")
                print(f"      [D] Filtrar por DOMINIO específico")
                
                choice = input("\n  Opción: ").strip().upper()
                
                if choice == "0":
                    get_detected_credentials(domain_filter=None, days_back=30)
                
                elif choice == "A":
                    # Todas las credenciales que coincidan con dominios registrados
                    print(f"\n  Buscando credenciales para {len(all_domains)} dominios registrados...")
                    print(f"  (Esto puede tomar un momento)\n")
                    
                    total_found = 0
                    results_by_domain = {}
                    
                    for dom in all_domains:
                        # Consulta silenciosa (sin detalles)
                        endpoint = f"{BASE_URL}/exposure-api/credentials"
                        params = {
                            "customer": CUSTOMER_ID,
                            "created": f"ge:{(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')}",
                            "status": "NEW,IN_TREATMENT",
                            "user": f"contains:{dom}",
                            "pageSize": 1
                        }
                        try:
                            resp = requests.get(endpoint, headers=HEADERS, params=params)
                            if resp.status_code == 200:
                                count = resp.json().get("pageable", {}).get("total", 0)
                                if count > 0:
                                    brand = domain_to_brand.get(dom) or "(sin marca)"
                                    results_by_domain[dom] = {"count": count, "brand": brand}
                                    total_found += count
                        except:
                            pass
                    
                    # Mostrar resumen agrupado
                    print(f"  {'='*50}")
                    print(f"  RESUMEN POR DOMINIO (Solo con credenciales)")
                    print(f"  {'='*50}")
                    
                    if results_by_domain:
                        for dom, info in sorted(results_by_domain.items(), key=lambda x: x[1]["count"], reverse=True):
                            print(f"  {dom:35} {info['count']:>6} creds  [{info['brand']}]")
                        
                        print(f"  {'='*50}")
                        print(f"  TOTAL: {total_found} credenciales en {len(results_by_domain)} dominios")
                    else:
                        print(f"  No se encontraron credenciales en los dominios registrados.")
                    
                elif choice == "B":
                    print(f"\n  Selecciona una marca:")
                    for i, brand in enumerate(brands, 1):
                        print(f"      [{i}] {brand['name']}")
                    
                    try:
                        brand_choice = int(input("\n  Marca #: ").strip())
                        if 1 <= brand_choice <= len(brands):
                            selected_brand = brands[brand_choice - 1]["name"]
                            brand_doms = brand_domains.get(selected_brand, [])
                            
                            if brand_doms:
                                print(f"\n  Buscando credenciales para {selected_brand}...")
                                # Consultar cada dominio de la marca
                                for dom in brand_doms:
                                    get_detected_credentials(domain_filter=dom, days_back=30, show_details=False)
                            else:
                                print(f"  ⚠️  La marca {selected_brand} no tiene dominios asociados.")
                    except ValueError:
                        print("  Entrada inválida.")
                        
                elif choice == "D":
                    print(f"\n  Dominios disponibles:")
                    for i, domain in enumerate(all_domains[:20], 1):
                        brand = domain_to_brand.get(domain) or "(sin marca)"
                        print(f"      [{i}] {domain} -> {brand}")
                    if len(all_domains) > 20:
                        print(f"      ... y {len(all_domains) - 20} más.")
                    
                    try:
                        dom_choice = int(input("\n  Dominio #: ").strip())
                        if 1 <= dom_choice <= len(all_domains):
                            selected_domain = all_domains[dom_choice - 1]
                            get_detected_credentials(domain_filter=selected_domain, days_back=30)
                    except ValueError:
                        print("  Entrada inválida.")
                else:
                    get_detected_credentials(domain_filter=None, days_back=30)
            else:
                get_detected_credentials(domain_filter=None, days_back=30)
    except:
        pass
    
    return risk_score


if __name__ == "__main__":
    main()