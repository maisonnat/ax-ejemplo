# Axur Risk Assessment Toolkit v4.0

> **Guia completo para implementar sistemas de avaliação de risco usando a API da Axur**

Este documento faz a ponte entre a [documentação oficial da Axur](https://docs.axur.com/pt/axur/api/) e a implementação prática de metodologias de risco.

🌐 **Idioma**: [Español](README.md) | [English](README.en.md) | **Português**

---

## 📋 Índice

1. [Resumo Executivo](#resumo-executivo)
2. [Configuração](#configuração)
3. [Metodologias Implementadas](#metodologias-implementadas)
   - [Risk Score v3.0 (KRI)](#risk-score-v30-kri)
   - [Análise DREAD](#análise-dread)
   - [Classificação STRIDE](#classificação-stride)
4. [Estrutura do Projeto](#estrutura-do-projeto)
5. [Endpoints da API](#endpoints-da-api)
6. [Exemplos Mock](#exemplos-mock)
7. [Personalização](#personalização)

---

## Resumo Executivo

### O que este toolkit faz?

| Metodologia | Pergunta de Negócio | Saída |
|:---|:---|:---|
| **Risk Score v3.0** | Como está minha postura de segurança geral? | Score 0-1000 |
| **DREAD** | Quais incidentes devo resolver primeiro? | Top 10 priorizado |
| **STRIDE** | Quais tipos de ataque me afetam mais? | Matriz de ameaças |
| **Credenciais** | Quais credenciais estão expostas? | Lista filtrada por domínio |
| **Filtro OnePixel** | Quais ameaças foram auto-detectadas? | Tickets por origem |

### Para quem é este documento?

- **👔 Executivos**: Explicações de negócio em cada seção
- **💻 Desenvolvedores**: Exemplos de código, JSON mock e links de documentação técnica

---

## Configuração

### Passo 1: Clonar o repositório

```bash
git clone https://github.com/yourusername/axur-risk-toolkit.git
cd axur-risk-toolkit
```

### Passo 2: Instalar dependências

```bash
pip install -r requirements.txt
```

### Passo 3: Criar `config.json`

```json
{
  "api_key": "SUA_API_KEY_AQUI",
  "customer_id": "SEU_CUSTOMER_ID",
  "base_url": "https://api.axur.com/gateway/1.0/api",
  "days_range": 30
}
```

### Passo 4: Obter sua API Key

1. Acesse [Axur Platform](https://one.axur.com)
2. Vá em **Preferências** → **API Keys**
3. Crie uma nova API Key com permissões de leitura

> 📖 **Documentação Axur**: [Authentication](https://docs.axur.com/pt/axur/api/#section/Authentication)

### Passo 5: Executar

```bash
python main.py
```

---

## Metodologias Implementadas

### Risk Score v3.0 (KRI)

#### 👔 Visão de Negócio

> "Me dê um número único que resuma quão seguro estou comparado à minha indústria"

O Risk Score avalia sua **postura de segurança geral** em uma escala de 0-1000:

| Score | Status | Significado |
|:---:|:---|:---|
| 800-1000 | 🟢 **EXCELENTE** | Baixo risco, manter monitoramento |
| 600-799 | 🟡 **BOM** | Risco moderado, revisar alertas |
| 400-599 | 🟠 **ALERTA** | Requer ações preventivas |
| 0-399 | 🔴 **CRÍTICO** | Atenção imediata necessária |

#### 💻 Visão Técnica

**Fórmula:**
```
Score = 1000 - (BaseScore × FatoresDePenalidade)
```

**5 Indicadores-Chave de Risco (KRIs):**

| KRI | Peso | Endpoint | Propósito |
|:---|:---:|:---|:---|
| Incidentes Ponderados | 40% | `/tickets-api/tickets` | Volume e severidade |
| Benchmark de Mercado | 20% | `/tickets-api/stats` | Comparação com a indústria |
| Stealer Logs | 15% | `/exposure-api` | Malware ativo |
| Eficiência Operacional | 15% | `/tickets-api/stats/takedown` | Velocidade de resolução |
| Impacto Reputacional | 10% | `/web-complaints` | Relatórios de vítimas |

---

### Análise DREAD

#### 👔 Visão de Negócio

> "Priorize minha fila de incidentes por risco real"

DREAD avalia cada incidente com 5 fatores (escala 1-10):

- **D**ano: Quanto dano poderia causar?
- **R**eprodutibilidade: Quão fácil é replicar?
- **E**xplorabilidade: Quão fácil é explorar?
- **A**fetados: Quantos usuários impactados?
- **D**escoberta: Quão fácil é descobrir?

Score Total = Média dos 5 fatores (1-10)

---

### Classificação STRIDE

#### 👔 Visão de Negócio

> "Quais são as principais estratégias de ataque contra nós?"

STRIDE agrupa ameaças em 6 categorias estratégicas:

| Categoria | Descrição | Exemplos |
|:---:|:---|:---|
| **S**poofing | Falsificação de identidade | Phishing, perfis falsos |
| **T**ampering | Modificação de dados | Apps falsos, uso indevido de marca |
| **R**epudio | Negação de ações | Vendas não autorizadas |
| **I**nfo Disclosure | Vazamento de dados | Vazamento de credenciais, exposição de BD |
| **D**enial of Service | Interrupção | Ransomware, malware |
| **E**levation | Escalação de privilégios | Stealer logs |

---

## Estrutura do Projeto

```
/
├── main.py                 # Aplicação principal (menu interativo)
├── config.json             # Configuração (não rastreado)
├── requirements.txt        # Dependências Python
│
├── /core                   # Camada de infraestrutura
│   ├── axur_client.py      # Conector reutilizável da API Axur
│   └── utils.py            # Utilitários compartilhados
│
├── /use_cases              # Módulos de lógica de negócio
│   ├── /risk_scoring       # Cálculo do Risk Score v3.0
│   ├── /threat_detection   # Filtro de origem OnePixel
│   └── /executive_reports  # Análise DREAD + STRIDE
│
└── MOCK_EXAMPLES.md        # Exemplos de resposta da API
```

---

## Endpoints da API

| Endpoint | Propósito | Documentação |
|:---|:---|:---|
| `/tickets-api/tickets` | Buscar tickets de incidentes | [Link](https://docs.axur.com/pt/axur/api/#tag/Tickets) |
| `/tickets-api/stats` | Estatísticas e métricas | [Link](https://docs.axur.com/pt/axur/api/#tag/Stats) |
| `/exposure-api/credentials` | Credenciais expostas | [Link](https://docs.axur.com/pt/axur/api/#tag/Exposure) |
| `/customers/customers` | Assets/marcas do cliente | [Link](https://docs.axur.com/pt/axur/api/#tag/Customers) |

---

## Exemplos Mock

Veja [MOCK_EXAMPLES.md](MOCK_EXAMPLES.md) para exemplos completos de resposta da API.

### Filtro de Detecção OnePixel

```python
from use_cases.threat_detection import filter_by_origin

# Obter tickets detectados pelo OnePixel
tickets = filter_by_origin(origin="onepixel", days_back=90)
print(f"Encontrados {len(tickets)} detecções OnePixel")
```

---

## Personalização

### Adicionando novos pesos de ameaças

Edite `use_cases/risk_scoring/calculator.py`:

```python
THREAT_WEIGHTS = {
    "ransomware-attack": 100,
    "phishing": 50,
    "seu-tipo-customizado": 75,  # Adicione seu peso customizado
    ...
}
```

### Adicionando novos mapeamentos STRIDE

Edite `use_cases/executive_reports/generator.py`:

```python
STRIDE_MAPPING = {
    "seu-tipo-customizado": "S",  # Mapeia para Spoofing
    ...
}
```

---

## Licença

Este projeto é para fins educacionais e de demonstração. Por favor, garanta conformidade com os termos de serviço da API da Axur.

---

*Construído com ❤️ para equipes de segurança*
