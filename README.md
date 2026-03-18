# Consulta de Preços (NAG)

Aplicação web interna (Flask) para **pesquisa e análise de preços** usando duas fontes:

- **Compras.gov.br (CATMAT)**: o usuário digita um **código CATMAT**, o sistema consulta a API pública do Compras.gov.br, faz limpeza automática e retorna **mínimo / mediana / média / máximo válido** + **IQR** e uma tabela de registros.
- **SerpAPI (Google Shopping)**: o usuário digita um **termo de busca**, o sistema consulta o Google Shopping via SerpAPI e retorna a lista de itens com link + estatísticas de preço quando possível.

O objetivo é acelerar a pesquisa, reduzindo ruído (kits, lotes, cadastros errados) e deixando o resultado **mais técnico e rastreável**.

---

## Como usar (visão do usuário)

### Aba 1 — Compras.gov.br (CATMAT)

1. Localize o código no Catálogo de Compras: `https://catalogo.compras.gov.br/cnbs-web/busca`
2. Digite o **código CATMAT**
3. Clique em **Buscar**
4. O sistema mostra:
   - **Resumo estatístico**: mínimo válido, mediana, média, máximo válido e IQR
   - **Registros considerados**: tabela ordenada por preço (menor → maior)

### Aba 2 — SerpAPI (Google Shopping)

1. Digite um termo (ex.: “mouse sem fio logitech”)
2. Clique em **Buscar**
3. O sistema mostra:
   - Tabela com **título, preço, loja e link**
   - Estatísticas quando o preço é extraível como número

---

## Regras de limpeza (CATMAT)

Importante: **CATMAT é genérico**. Para deixar o resultado mais consistente, aplicamos uma limpeza automática em `src/core/cleaning.py`.

### 1) Filtro por descrição

Remove registros cuja descrição contenha termos típicos de “não é um item unitário”, por exemplo:

- KIT, LOTE, COMBO, CONJUNTO, PACK, CAIXA, ESTOJO, CX, PACOTE

### 2) Filtro por unidade de fornecimento

Quando a API retorna unidade, mantemos apenas:

- **UN** / **UNIDADE**

Isso reduz casos de “caixa com N unidades” ou “kit” marcado como unitário.

### 3) Filtro por data

Se existir data, o sistema mantém apenas:

- **últimos 24 meses**

Isso evita distorção por preços antigos (2021/2022/2023 etc.).

### 4) Outliers por mediana (corte relativo)

Depois de calcular a mediana, removemos valores acima de:

- **4 × mediana**

### 5) Outliers por IQR (intervalo interquartil)

Aplicamos IQR sobre o conjunto já filtrado e calculamos também:

- **Q1 e Q3** (mostrados como “IQR: de Q1 a Q3”)

> Mesmo com filtros, é recomendado revisar **descrição detalhada**, **marca** e **unidade** antes de usar os números em processos formais.

---

## Arquitetura do projeto

- **`app.py`**: cria o Flask e registra os blueprints
- **`src/routes/`**:
  - `compras.py`: rota `/` (CATMAT)
  - `serpapi.py`: rota `/serpapi` (SerpAPI)
- **`src/services/`**:
  - `compras_gov.py`: consulta a API do Compras.gov.br e normaliza colunas
  - `serpapi_client.py`: cliente SerpAPI (lê chave do `.env`)
- **`src/core/`**:
  - `cleaning.py`: regras de limpeza e cálculo de estatísticas
  - `formatting.py`: formatação de moeda
- **`templates/`**:
  - `base.html`: layout + navegação por abas
  - `compras.html`, `serpapi.html`
  - `partials/_stats_cards.html`: cards reutilizáveis
- **`static/`**:
  - `styles.css`: ajustes visuais

---

## Variáveis de ambiente (.env)

Crie um `.env` baseado no `.env.example`.

- **`SERPAPI_API_KEY`**: obrigatório para a aba SerpAPI
- **`PORT`**: opcional (default 5000)

Exemplo:

```bash
SERPAPI_API_KEY="SUA_CHAVE_AQUI"
PORT=5000
```

---

## Como rodar o projeto (passo a passo)

### 1) Criar e ativar o ambiente virtual

```bash
cd /Users/lucasfontoura/Documents/lucas/python/consulta-preco-nag
python3 -m venv venv
source venv/bin/activate
```

### 2) Instalar dependências

```bash
pip install -r requirements.txt
```

### 3) Configurar `.env`

```bash
cp .env.example .env
```

Edite o arquivo `.env` e preencha `SERPAPI_API_KEY`.

### 4) Executar

```bash
python app.py
```

### 5) Acessar no navegador

- Compras.gov.br (CATMAT): `http://127.0.0.1:5000/`
- SerpAPI (Google Shopping): `http://127.0.0.1:5000/serpapi`


