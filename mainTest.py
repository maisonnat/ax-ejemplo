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

# Rango de fechas por defecto (se puede sobreescribir)
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=DAYS_RANGE)
FMT_DATE = "%Y-%m-%dT%H:%M:%S"

def get_date_range_selector():
    """
    Solicita al usuario seleccionar un rango de fechas.
    Retorna (start_date, end_date) como objetos datetime.
    """
    print("\n  📅 Selección de Rango de Fechas:")
    print("    [1] Últimos 7 días")
    print("    [2] Últimos 30 días (Default)")
    print("    [3] Últimos 90 días")
    print("    [4] Personalizado (YYYY-MM-DD)")
    
    choice = input("\n  Opción [1-4] (Enter = 30 días): ").strip()
    
    end = datetime.now()
    
    if choice == "1":
        start = end - timedelta(days=7)
    elif choice == "3":
        start = end - timedelta(days=90)
    elif choice == "4":
        try:
            s_str = input("    Fecha inicio (YYYY-MM-DD): ").strip()
            e_str = input("    Fecha fin    (YYYY-MM-DD): ").strip()
            start = datetime.strptime(s_str, "%Y-%m-%d")
            end = datetime.strptime(f"{e_str} 23:59:59", "%Y-%m-%d %H:%M:%S")
        except:
            print("  ⚠️  Formato inválido. Usando 30 días.")
            start = end - timedelta(days=30)
    else:
        start = end - timedelta(days=30)
        
    return start, end


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

def get_credential_exposure_score(start_date, end_date):
    """
    Calcula el índice de higiene basado en:
    1. Formato de la fuga (STEALER LOG = crítico)
    2. Tipo de contraseña (PLAIN = máximo riesgo)
    
    Fuente: /exposure-api/credentials
    """
    endpoint = f"{BASE_URL}/exposure-api/credentials"
    
    params = {
        "status": "NEW,IN_TREATMENT",
        "created": f"ge:{start_date.strftime('%Y-%m-%d')}",
        "created": f"le:{end_date.strftime('%Y-%m-%d')}",
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

def get_response_efficiency_score(start_date, end_date):
    endpoint = f"{BASE_URL}/tickets-api/stats/takedown/uptime"
    params = {
        "customer": CUSTOMER_ID,
        "from": start_date.strftime(FMT_DATE),
        "to": end_date.strftime(FMT_DATE)
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

def get_incident_volume_score(start_date, end_date):
    endpoint = f"{BASE_URL}/tickets-api/stats/incident/count/ticket-types"
    params = {
        "customer": CUSTOMER_ID,
        "from": start_date.strftime(FMT_DATE),
        "to": end_date.strftime(FMT_DATE),
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

def get_real_damage_score(start_date, end_date):
    damage_score = 200
    
    endpoint = f"{BASE_URL}/web-complaints/results"
    params = {
        "initialDate": start_date.strftime("%Y-%m-%d"),
        "finalDate": end_date.strftime("%Y-%m-%d"),
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

def calculate_risk_score(start_date, end_date):
    print(f"\n{'='*60}")
    print(f"  PUNTUACIÓN DE POSTURA DE RIESGO v2.0 - {CUSTOMER_ID}")
    print(f"{'='*60}")
    print(f"  Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
    print(f"{'='*60}\n")
    
    print("[1/4] Calculando Índice de Higiene (Exposure API)...")
    hygiene_penalty = get_credential_exposure_score(start_date, end_date)
    hygiene_score = max(0, 300 - hygiene_penalty)
    print(f"      → Puntuación: {hygiene_score}/300\n")
    
    print("[2/4] Calculando Índice de Respuesta (Takedown Uptime)...")
    response_score = get_response_efficiency_score(start_date, end_date)
    print(f"      → Puntuación: {response_score}/300\n")
    
    print("[3/4] Calculando Volumen de Amenazas (Ticket Types)...")
    volume_score = get_incident_volume_score(start_date, end_date)
    print(f"      → Puntuación: {volume_score}/200\n")
    
    print("[4/4] Calculando Índice de Daño Real (Web Complaints)...")
    damage_score = get_real_damage_score(start_date, end_date)
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

def get_incidents_for_period(start_date, end_date):
    """
    Obtiene TODOS los incidentes creados en un rango de fechas.
    Endpoint: /tickets-api/tickets
    """
    endpoint = f"{BASE_URL}/tickets-api/tickets"
    # Construir params como lista de tuplas para permitir claves duplicadas (open.date)
    # Usamos T00:00:00 y T23:59:59 para asegurar cobertura del día completo
    s_str = start_date.strftime('%Y-%m-%d')
    params_list = [
        ("ticket.customer", CUSTOMER_ID),
        ("open.date", f"ge:{s_str}T00:00:00")
    ]
    
    if end_date:
        e_str = end_date.strftime('%Y-%m-%d')
        params_list.append(("open.date", f"le:{e_str}T23:59:59"))
        
    params_list.append(("pageSize", "200"))
    params_list.append(("sortBy", "open.date"))
    params_list.append(("order", "desc"))

    all_tickets = []
    page = 1
    
    try:
        while True:
            # Para paginación, necesitamos actualizar 'page' en la lista de tuplas.
            # Como es una lista, es mejor reconstruirla o añadir al final si requests lo maneja bien.
            # Requests acepta lista de tuplas.
            current_params = params_list + [("page", str(page))]
            
            response = requests.get(endpoint, headers=HEADERS, params=current_params)
            
            if response.status_code == 200:
                data = response.json()
                tickets = data.get("tickets", [])
                
                if not tickets:
                    break
                    
                all_tickets.extend(tickets)
                
                if len(tickets) < 200: # pageSize hardcoded checks
                    break
                    
                page += 1
            else:
                print(f"  [Error] API Status {response.status_code}: {response.text}")
                break
                
    except Exception as e:
        print(f"  [Error] Obteniendo detalle de incidentes: {e}")
        
    return all_tickets
                


def get_weighted_incidents(brand_filter=None, start_date=None, end_date=None, exclude_discarded=False):
    """
    KRI 1: Volumen ponderado de incidentes por gravedad.
    
    MODIFICADO v2: Ahora usa /tickets-api/tickets para permitir filtrado por Asset/Marca.
    Si brand_filter es None, calcula para todo el tenant (comportamiento legacy).
    
    MODIFICADO v3: Soporte para excluir tickets descartados (falsos positivos).
    """
    # Usar fechas globales si no se proveen (compatibilidad)
    if not start_date: start_date = START_DATE
    if not end_date: end_date = END_DATE

    # 1. Obtener lista detallada de tickets
    print(f"      Consultando detalle de incidentes (para filtrado exacto)...")
    tickets = get_incidents_for_period(start_date, end_date)
    
    weighted_score = 0
    total_incidents = 0
    breakdown = {}
    
    ignored_count = 0
    discarded_filtered_count = 0
    
    for ticket in tickets:
        detection = ticket.get("detection", {})
        
        # Filtrado por Marca/Asset
        if brand_filter:
            assets = detection.get("assets", [])
            # Verificamos si la marca solicitada está en la lista de assets del ticket
            if brand_filter not in assets:
                ignored_count += 1
                continue
        
        # Filtrado por Estado/Resolución (Falsos Positivos)
        if exclude_discarded:
            # Si el usuario quiere solo "amenazas reales", descartamos lo que Axur marcó como "discarded"
            # Ojo: Un ticket cerrado puede ser Threats Real (Takedown) o Falso Positivo (Discarded).
            # Filtramos solo si resolution es explícitamente 'discarded'.
            status = detection.get("status")
            resolution = detection.get("resolution")
            
            if resolution == "discarded":
                discarded_filtered_count += 1
                continue
                
        # Procesar ticket válido
        t_type = detection.get("type", "unknown")
        
        # Ignorar tickets fuera de rango estricto si la API trajo de más 
        # (aunque el filtro ge: lo maneja bien)
        
        weight = INCIDENT_WEIGHTS.get(t_type, 10)
        
        weighted_score += weight
        total_incidents += 1
        
        if t_type not in breakdown:
            breakdown[t_type] = {"count": 0, "weight": weight, "score": 0}
        
        breakdown[t_type]["count"] += 1
        breakdown[t_type]["score"] += weight
    
    if brand_filter:
        print(f"      ℹ️  Filtrados {ignored_count} incidentes de otras marcas.")
        
    if exclude_discarded:
        print(f"      ℹ️  Excluidos {discarded_filtered_count} falsos positivos (Discarded).")
        
    print(f"      ✅  Procesados {total_incidents} incidentes.")
                    
    return weighted_score, total_incidents, breakdown


def get_market_benchmark(end_date):
    """
    KRI 2: Comparativa con la MEDIANA del segmento de mercado del cliente.
    Endpoint: /tickets-api/stats/incident/customer/market-segment/median
    """
    endpoint = f"{BASE_URL}/tickets-api/stats/incident/customer/market-segment/median"
    params = {
        "customer": CUSTOMER_ID,
        "to": end_date.strftime("%Y-%m-%d"),
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


def get_stealer_log_count(start_date, end_date):
    """
    KRI 3: Conteo de credenciales de Stealer Logs (malware activo).
    Endpoint: /exposure-api/credentials con leak.format=STEALER LOG
    """
    endpoint = f"{BASE_URL}/exposure-api/credentials"
    params = {
        "customer": CUSTOMER_ID,
        "status": "NEW,IN_TREATMENT",
        "created": f"ge:{start_date.strftime('%Y-%m-%d')}",
        "created": f"le:{end_date.strftime('%Y-%m-%d')}",
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


def get_operational_efficiency(start_date, end_date):
    """
    KRI 4: Eficiencia operativa basada en tiempos de resolución.
    Endpoint: /tickets-api/stats/takedown/uptime
    """
    endpoint = f"{BASE_URL}/tickets-api/stats/takedown/uptime"
    params = {
        "customer": CUSTOMER_ID,
        "from": start_date.strftime(FMT_DATE),
        "to": end_date.strftime(FMT_DATE)
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


def get_web_complaints_count(start_date, end_date):
    """
    KRI 5: Conteo de quejas web (riesgo reputacional).
    Endpoint: /web-complaints/results
    """
    endpoint = f"{BASE_URL}/web-complaints/results"
    params = {
        "initialDate": start_date.strftime("%Y-%m-%d"),
        "finalDate": end_date.strftime("%Y-%m-%d"),
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


def calculate_risk_score_v3(brand_filter=None, start_date=None, end_date=None, exclude_discarded=False):
    """
    Risk Score v3.0 - Modelo KRI (Key Risk Indicators)
    
    Fórmula: Score = Base × (1 + StealerFactor) × (1 + SlowFactor) × (1 + ComplaintsFactor)
    
    Donde Base = min(1000, WeightedIncidents / MarketRatio)
    """
    # Defaults locales si no vienen
    if not start_date: start_date = START_DATE
    if not end_date: end_date = END_DATE

    print(f"\n{'='*65}")
    print(f"  ╔═══════════════════════════════════════════════════════════╗")
    if brand_filter:
        print(f"  ║  RISK SCORE v3.0 (KRI) - {brand_filter:^20}           ║")
    else:
        print(f"  ║  RISK SCORE v3.0 (KRI) - {CUSTOMER_ID:^20}           ║")
    print(f"  ╚═══════════════════════════════════════════════════════════╝")
    print(f"  Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
    if exclude_discarded:
        print(f"  Filtro:  EXCLUYENDO DESCARTADOS (Solo Activos)")
    print(f"{'='*65}\n")
    
    # --- KRI 1: Weighted Incidents ---
    print("[1/5] Analizando Volumen Ponderado de Incidentes...")
    weighted_score, total_incidents, breakdown = get_weighted_incidents(brand_filter, start_date, end_date, exclude_discarded)
    
    top_threats = sorted(breakdown.items(), key=lambda x: x[1]["score"], reverse=True)[:3]
    if top_threats:
        print(f"      Top 3 amenazas:")
        for t_type, info in top_threats:
            print(f"        • {t_type}: {info['count']} × {info['weight']} = {info['score']} pts")
    print(f"      → Volumen ponderado: {weighted_score} pts ({total_incidents} incidentes)\n")
    
    # --- KRI 2: Market Benchmark ---
    print("[2/5] Obteniendo Benchmark del Sector...")
    market_segment, sector_median, reference_month = get_market_benchmark(end_date)
    
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
    stealer_count, plain_count = get_stealer_log_count(start_date, end_date)
    
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
    uptime_data, slow_count, total_count = get_operational_efficiency(start_date, end_date)
    
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
    reputational_count = get_web_complaints_count(start_date, end_date)
    
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
# DREAD ANALYSIS
# =============================================================================

# Mapeo STRIDE: tipo de ticket -> categoría
STRIDE_MAPPING = {
    # Spoofing (Suplantación)
    "phishing": "S",
    "fake-social-media-profile": "S",
    "executive-fake-social-media-profile": "S",
    "similar-domain-name": "S",
    # Tampering (Modificación)
    "fraudulent-brand-use": "T",
    "fake-mobile-app": "T",
    # Repudiation (Repudio)
    "unauthorized-sale": "R",
    "unauthorized-distribution": "R",
    # Information Disclosure (Fuga de Información)
    "corporate-credential-leak": "I",
    "code-secret-leak": "I",
    "database-exposure": "I",
    "data-exposure-website": "I",
    "data-exposure-message": "I",
    "other-sensitive-data": "I",
    "executive-credential-leak": "I",
    "executive-personalinfo-leak": "I",
    # Denial of Service
    "ransomware-attack": "D",
    "infrastructure-exposure": "D",
    "malware": "D",
    # Elevation of Privilege
    "infostealer-credential": "E",
    "executive-card-leak": "E",
    "executive-mobile-phone": "E",
}

STRIDE_NAMES = {
    "S": "Spoofing (Suplantación)",
    "T": "Tampering (Modificación)",
    "R": "Repudiation (Repudio)",
    "I": "Information Disclosure (Fuga de Info)",
    "D": "Denial of Service (Interrupción)",
    "E": "Elevation of Privilege (Escalamiento)",
}

# Pesos DREAD por tipo de ticket
DREAD_REPRODUCIBILITY = {
    "phishing": 9,
    "fake-social-media-profile": 8,
    "similar-domain-name": 7,
    "malware": 6,
    "ransomware-attack": 5,
    "corporate-credential-leak": 4,
    "infostealer-credential": 8,
}

def get_open_tickets(max_tickets=100, start_date=None):
    """
    Obtiene tickets abiertos/incidentes del cliente.
    Endpoint: GET /tickets-api/tickets
    """
    if not start_date: start_date = START_DATE
    
    endpoint = f"{BASE_URL}/tickets-api/tickets"
    params = {
        "ticket.customer": CUSTOMER_ID,
        "status": "open,incident,treatment",
        "open.date": f"ge:{start_date.strftime('%Y-%m-%d')}",
        "pageSize": max_tickets,
        "sortBy": "open.date",
        "order": "desc"
    }
    
    tickets = []
    try:
        response = requests.get(endpoint, headers=HEADERS, params=params)
        if response.status_code == 200:
            data = response.json()
            tickets = data.get("tickets", [])
    except Exception as e:
        print(f"  [Error] Obteniendo tickets: {e}")
    
    return tickets


def calculate_dread_score(ticket):
    """
    Calcula el score DREAD (1-10) para un ticket individual.
    
    D = Damage (Daño potencial)
    R = Reproducibility (Facilidad de replicar)
    E = Exploitability (Facilidad de explotar)
    A = Affected Users (Usuarios afectados)
    D = Discoverability (Facilidad de descubrir)
    """
    detection = ticket.get("detection", {})
    ticket_info = ticket.get("ticket", {})
    
    ticket_type = detection.get("type", "unknown")
    criticality = detection.get("criticality", "medium")
    collector = ticket_info.get("creation.collector", "")
    prediction_risk = float(detection.get("prediction.risk", 0.5))
    
    # D - Damage: basado en criticality
    damage_map = {"high": 9, "medium": 6, "low": 3}
    D = damage_map.get(criticality, 5)
    
    # R - Reproducibility: basado en tipo de ticket
    R = DREAD_REPRODUCIBILITY.get(ticket_type, 5)
    
    # E - Exploitability: basado en prediction.risk de Axur
    E = int(prediction_risk * 10)
    
    # A - Affected Users: estimado por tipo
    if "executive" in ticket_type:
        A = 9  # Ejecutivos = alto impacto
    elif "credential" in ticket_type:
        A = 7  # Credenciales = muchos usuarios
    elif "phishing" in ticket_type:
        A = 6  # Phishing = clientes expuestos
    else:
        A = 4
    
    # D - Discoverability: basado en fuente/collector
    if "telegram" in collector.lower() or "twitter" in collector.lower():
        D2 = 9  # Público = fácil de descubrir
    elif "deep" in collector.lower() or "dark" in collector.lower():
        D2 = 4  # Dark web = difícil
    else:
        D2 = 6
    
    dread_score = (D + R + E + A + D2) / 5
    
    return {
        "score": round(dread_score, 1),
        "components": {"D": D, "R": R, "E": E, "A": A, "D2": D2},
        "ticket_key": ticket_info.get("ticketKey", ""),
        "type": ticket_type,
        "reference": ticket_info.get("reference", "")[:50],
        "criticality": criticality
    }


def analyze_dread(start_date=None, end_date=None):
    """
    Análisis DREAD: Prioriza tickets por score de riesgo.
    """
    if not start_date: start_date = START_DATE
    if not end_date: end_date = END_DATE
    
    print(f"\n{'='*70}")
    print(f"  ╔════════════════════════════════════════════════════════════════╗")
    print(f"  ║              ANÁLISIS DREAD - Priorización de Riesgo          ║")
    print(f"  ╚════════════════════════════════════════════════════════════════╝")
    print(f"  Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
    print(f"{'='*70}")
    print(f"\n  📖 ¿Qué es DREAD?")
    print(f"  DREAD evalúa cada incidente con 5 factores (escala 1-10):")
    print(f"    D = Damage        - ¿Cuánto daño puede causar?")
    print(f"    R = Reproducibility - ¿Qué tan fácil es replicarlo?")
    print(f"    E = Exploitability  - ¿Qué tan fácil es explotarlo?")
    print(f"    A = Affected Users  - ¿Cuántos usuarios afectados?")
    print(f"    D = Discoverability - ¿Qué tan fácil es descubrirlo?")
    print(f"\n  Score Final = Promedio de los 5 factores (1-10)")
    print(f"{'='*70}\n")
    
    print("  Obteniendo tickets abiertos...")
    tickets = get_open_tickets(50, start_date)
    
    if not tickets:
        print("  ⚠️  No se encontraron tickets abiertos en el período.")
        return []
    
    print(f"  ✅ {len(tickets)} tickets encontrados. Calculando scores DREAD...\n")
    
    # Calcular DREAD para cada ticket
    dread_results = []
    for ticket in tickets:
        result = calculate_dread_score(ticket)
        dread_results.append(result)
    
    # Ordenar por score (mayor = más crítico)
    dread_results.sort(key=lambda x: x["score"], reverse=True)
    
    # Mostrar top 10
    print(f"  {'─'*66}")
    print(f"  TOP 10 TICKETS MÁS CRÍTICOS (por DREAD Score)")
    print(f"  {'─'*66}")
    print(f"  {'#':>3} {'Score':>6} {'Ticket':>8} {'Tipo':<25} {'Crit':<6}")
    print(f"  {'─'*66}")
    
    for i, r in enumerate(dread_results[:10], 1):
        score_color = "🔴" if r["score"] >= 7 else "🟠" if r["score"] >= 5 else "🟡"
        print(f"  {i:>3} {score_color} {r['score']:>4} {r['ticket_key']:>8} {r['type']:<25} {r['criticality']:<6}")
    
    print(f"  {'─'*66}")
    
    # Resumen estadístico
    avg_score = sum(r["score"] for r in dread_results) / len(dread_results)
    high_risk = len([r for r in dread_results if r["score"] >= 7])
    
    print(f"\n  📊 RESUMEN:")
    print(f"      Score promedio: {avg_score:.1f}/10")
    print(f"      Tickets alto riesgo (>=7): {high_risk}")
    print(f"      Tickets analizados: {len(dread_results)}")
    
    return dread_results


def classify_stride(start_date=None, end_date=None):
    """
    Clasificación STRIDE: Agrupa tickets por categoría de amenaza.
    """
    if not start_date: start_date = START_DATE
    if not end_date: end_date = END_DATE

    print(f"\n{'='*70}")
    print(f"  ╔════════════════════════════════════════════════════════════════╗")
    print(f"  ║           CLASIFICACIÓN STRIDE - Matriz de Amenazas           ║")
    print(f"  ╚════════════════════════════════════════════════════════════════╝")
    print(f"  Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
    print(f"{'='*70}")
    print(f"\n  📖 ¿Qué es STRIDE?")
    print(f"  STRIDE clasifica amenazas en 6 categorías:")
    print(f"    S = Spoofing           - Suplantación de identidad")
    print(f"    T = Tampering          - Modificación no autorizada")
    print(f"    R = Repudiation        - Negación de acciones")
    print(f"    I = Info Disclosure    - Fuga de información")
    print(f"    D = Denial of Service  - Interrupción de servicio")
    print(f"    E = Elevation          - Escalamiento de privilegios")
    print(f"\n  Útil para: Identificar qué tipo de ataques predominan")
    print(f"{'='*70}\n")
    
    print("  Obteniendo tickets...")
    tickets = get_open_tickets(200, start_date)
    
    if not tickets:
        print("  ⚠️  No se encontraron tickets.")
        return {}
    
    # Clasificar por STRIDE
    stride_counts = {"S": 0, "T": 0, "R": 0, "I": 0, "D": 0, "E": 0, "?": 0}
    stride_examples = {"S": [], "T": [], "R": [], "I": [], "D": [], "E": [], "?": []}
    
    for ticket in tickets:
        detection = ticket.get("detection", {})
        ticket_type = detection.get("type", "unknown")
        ticket_key = ticket.get("ticket", {}).get("ticketKey", "")
        
        category = STRIDE_MAPPING.get(ticket_type, "?")
        stride_counts[category] += 1
        if len(stride_examples[category]) < 3:
            stride_examples[category].append(f"{ticket_key}:{ticket_type}")
    
    total = sum(stride_counts.values())
    
    print(f"  {'─'*66}")
    print(f"  DISTRIBUCIÓN DE AMENAZAS POR CATEGORÍA STRIDE")
    print(f"  {'─'*66}")
    
    # Ordenar por conteo
    sorted_stride = sorted(stride_counts.items(), key=lambda x: x[1], reverse=True)
    
    for cat, count in sorted_stride:
        if cat == "?":
            continue
        pct = (count / total * 100) if total > 0 else 0
        bar = "█" * int(pct / 5)
        name = STRIDE_NAMES.get(cat, "Desconocido")
        emoji = "🔴" if pct > 30 else "🟠" if pct > 15 else "🟡"
        print(f"  {emoji} [{cat}] {name:<35} {count:>4} ({pct:>5.1f}%) {bar}")
    
    if stride_counts["?"] > 0:
        print(f"  ⚪ [?] Sin clasificar                              {stride_counts['?']:>4}")
    
    print(f"  {'─'*66}")
    print(f"  Total: {total} tickets analizados")
    
    # Identificar amenaza dominante
    dominant = max(stride_counts.items(), key=lambda x: x[1] if x[0] != "?" else 0)
    if dominant[1] > 0:
        print(f"\n  🎯 AMENAZA DOMINANTE: {STRIDE_NAMES.get(dominant[0], 'N/A')}")
        print(f"     Representa {dominant[1]/total*100:.0f}% de los incidentes")
    
    return stride_counts


def show_main_menu():
    """
    Muestra el menú principal con explicaciones para cada opción.
    """
    print(f"\n{'='*70}")
    print(f"  ╔════════════════════════════════════════════════════════════════╗")
    print(f"  ║       AXUR RISK ASSESSMENT v4.0 - {CUSTOMER_ID:^20}       ║")
    print(f"  ╚════════════════════════════════════════════════════════════════╝")
    print(f"{'='*70}")
    print(f"\n  Selecciona el tipo de análisis que deseas ejecutar:\n")
    
    print(f"  ┌─────────────────────────────────────────────────────────────────┐")
    print(f"  │  [1] RISK SCORE v3.0 (KRI)                                      │")
    print(f"  │      📊 Visión ejecutiva: Score único 0-1000                    │")
    print(f"  │      Compara tu postura vs el mercado. Ideal para reportes.     │")
    print(f"  ├─────────────────────────────────────────────────────────────────┤")
    print(f"  │  [2] ANÁLISIS DREAD                                             │")
    print(f"  │      🎯 Priorización: ¿Qué incidentes atender primero?          │")
    print(f"  │      Score individual por ticket según impacto y explotabilidad.│")
    print(f"  ├─────────────────────────────────────────────────────────────────┤")
    print(f"  │  [3] CLASIFICACIÓN STRIDE                                       │")
    print(f"  │      📈 Matriz de amenazas: ¿Qué tipos de ataque predominan?    │")
    print(f"  │      Agrupa incidentes en 6 categorías estratégicas.            │")
    print(f"  ├─────────────────────────────────────────────────────────────────┤")
    print(f"  │  [4] REPORTE COMPLETO                                           │")
    print(f"  │      📋 Ejecuta los 3 análisis anteriores                       │")
    print(f"  ├─────────────────────────────────────────────────────────────────┤")
    print(f"  │  [5] CONSULTAR CREDENCIALES                                     │")
    print(f"  │      🔐 Buscar credenciales expuestas por dominio               │")
    print(f"  └─────────────────────────────────────────────────────────────────┘")
    print(f"\n  [0] Salir\n")


def main():
    """Función principal con menú interactivo."""
    
    while True:
        show_main_menu()
        
        try:
            choice = input("  Selecciona una opción [0-5]: ").strip()
        except:
            break
        
        if choice == "0":
            print("\n  👋 ¡Hasta luego!\n")
            break
            
        elif choice == "1":
            # Risk Score v3.0 (KRI)
            start, end = get_date_range_selector()
            
            # Preguntar si desea filtrar por marca
            brands, domain_to_brand = get_customer_assets()
            brand_filter = None
            
            if brands:
                print("\n  ¿Desea filtrar por una Marca/Asset específico? (Recomendado para accuracy)")
                filter_yn = input("  [S/n]: ").strip().lower()
                
                if filter_yn in ["s", "si", "y", "yes", ""]:
                    print("\n  Marcas disponibles:")
                    for i, b in enumerate(brands, 1):
                        name = b.get("name", "N/A")
                        key = b.get("key", "")
                        print(f"    [{i}] {name} ({key})")
                    
                    try:
                        idx = int(input("\n  Seleccione marca #: ")) - 1
                        if 0 <= idx < len(brands):
                            selected = brands[idx]
                            brand_filter = selected.get("key") or selected.get("name")
                            print(f"  ✅ Filtrando por: {brand_filter}")
                    except:
                        pass

            # Preguntar si desea excluir tickets descartados/cerrados
            exclude_discarded = False
            print("\n  ¿Excluir tickets descartados/falsos positivos? (Mostrar solo Amenazas Activas)")
            discard_yn = input("  [S/n]: ").strip().lower()
            if discard_yn in ["s", "si", "y", "yes", ""]:
                exclude_discarded = True
                print("  ✅ Excluyendo falsos positivos.")
            else:
                print("  ⚠️  Incluyendo todo el volumen histórico.")
            
            calculate_risk_score_v3(brand_filter, start, end, exclude_discarded)
            input("\n  Presiona ENTER para continuar...")
            
        elif choice == "2":
            # Análisis DREAD
            start, end = get_date_range_selector()
            analyze_dread(start, end)
            input("\n  Presiona ENTER para continuar...")
            
        elif choice == "3":
            # Clasificación STRIDE
            start, end = get_date_range_selector()
            classify_stride(start, end)
            input("\n  Presiona ENTER para continuar...")
            
        elif choice == "4":
            # Reporte Completo
            print("\n" + "="*70)
            print("  EJECUTANDO REPORTE COMPLETO...")
            print("="*70)
            
            start, end = get_date_range_selector()
            
            # Se podría preguntar marca una vez y pasarla, pero por simplicidad
            # dejamos el flujo de Risk Score que ya la pregunta
            # Aunque siendo reporte completo, sería ideal preguntar una sola vez
            # Para esta iteración, que pregunte el Risk Score individualmente
            
            calculate_risk_score_v3(None, start, end) # Risk score preguntará marca si se corre interactivo... pero calculate_risk_score_v3 ya no pregunta, lo hace Main.
            # ERROR: calculate_risk_score_v3 NO pregunta, recibe param. 
            # DEBEMOS preguntar filtro de marca aqui tambien si queremos consistencia.
            # O asumimos 'global' para el reporte completo.
            
            # Corrección: El Main pregunta antes de llamar a calculate_risk_score_v3. 
            # Aquí en "Reporte Completo", llamaremos sin filtro (None) para visión global,
            # o implementamos pregunta si el usuario quiere.
            # Por simplicidad, "Reporte Completo" asumiremos visión global para no complicar el flujo.
            
            analyze_dread(start, end)
            classify_stride(start, end)
            input("\n  Presiona ENTER para continuar...")
            
        elif choice == "5":
            # Consultar Credenciales
            brands, domain_to_brand = get_customer_assets()
            all_domains = list(domain_to_brand.keys())
            
            if all_domains:
                print(f"\n  Opciones de filtro:")
                print(f"    [0] Sin filtro (todas las credenciales)")
                print(f"    [A] Todas con dominios del cliente")
                print(f"    [B] Filtrar por Marca (Brand)")
                print(f"    [D] Filtrar por Dominio específico")
                
                try:
                    filter_choice = input("\n  Opción: ").strip().upper()
                    
                    if filter_choice == "0":
                        get_detected_credentials(domain_filter=None, days_back=30)
                    elif filter_choice == "A":
                        print("\n  Buscando en todos los dominios del cliente...")
                        for domain in all_domains[:10]:
                            print(f"    Consultando {domain}...")
                            get_detected_credentials(domain_filter=domain, days_back=30, show_details=False)
                    elif filter_choice == "B" and brands:
                        print("\n  Marcas disponibles:")
                        for i, b in enumerate(brands, 1):
                            print(f"    [{i}] {b['name']}")
                        brand_idx = int(input("\n  Marca #: ").strip()) - 1
                        if 0 <= brand_idx < len(brands):
                            brand_name = brands[brand_idx]["name"]
                            brand_domains = [d for d, bn in domain_to_brand.items() if bn == brand_name]
                            for bd in brand_domains:
                                get_detected_credentials(domain_filter=bd, days_back=30)
                    elif filter_choice == "D":
                        print("\n  Dominios disponibles:")
                        for i, d in enumerate(all_domains[:15], 1):
                            print(f"    [{i}] {d}")
                        dom_idx = int(input("\n  Dominio #: ").strip()) - 1
                        if 0 <= dom_idx < len(all_domains):
                            get_detected_credentials(domain_filter=all_domains[dom_idx], days_back=30)
                    else:
                        get_detected_credentials(domain_filter=None, days_back=30)
                except:
                    pass
            else:
                get_detected_credentials(domain_filter=None, days_back=30)
            
            input("\n  Presiona ENTER para continuar...")
        
        else:
            print("\n  ⚠️  Opción no válida. Intenta de nuevo.")


if __name__ == "__main__":
    main()