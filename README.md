# Pesquisa de Preços — Compras.gov.br + SerpAPI

Aplicação web interna desenvolvida em **Flask** para **pesquisa e análise de preços**, combinando:

- **Compras.gov.br (CATMAT)**: consulta à API pública de Dados Abertos para registros de compras governamentais.
- **SerpAPI (Google Shopping)**: consulta à API externa para pesquisa rápida de preços na internet.

---

## Sobre

Esta ferramenta acelera a pesquisa de preços trazendo:

- **Resumo estatístico** (mínimo, mediana, média, máximo e IQR)
- **Tabela de resultados** para auditoria rápida
- **Melhorias de UX** (loading ao pesquisar e limpeza automática ao recarregar)

> Observação: as fontes são diferentes. No **Compras.gov.br** há limpeza/normalização de dados; na **SerpAPI** os resultados refletem a internet e podem misturar kits/caixas/unidades.

---

## Funcionalidades

- Consulta por **código CATMAT** (Compras.gov.br)
- Consulta por **termo de busca** (SerpAPI / Google Shopping)
- Feedback visual com **indicador de carregamento** durante a requisição
- Exibição de **tabela** + **cards** de estatística (min/mediana/média/max/IQR)
- Preços formatados em **pt-BR** (`R$ 1.234,56`)
- Parser de preço mais tolerante (remove sufixos como “agora”, “à vista”, “a partir de”, etc.)
- Limpeza automática do estado ao **recarregar a página** (evita reenvio de formulário/POST)

---

## Pré-requisitos

- Python 3.10+

---

## Como executar localmente

### 1) Entrar na pasta do projeto

```bash
cd /Users/lucasfontoura/Documents/lucas/python/consulta-preco-nag
```

### 2) Criar e ativar o ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3) Instalar dependências

```bash
pip install -r requirements.txt
```

### 4) Configurar `.env`

```bash
cp .env.example .env
```

Edite o arquivo `.env` e preencha:

- `SERPAPI_API_KEY` (obrigatório para a aba SerpAPI)
- `PORT` (opcional; default 5000)

### 5) Executar a aplicação

```bash
python3 app.py
```

---

## Acesso

Após executar, acesse:

- Compras.gov.br (CATMAT): `http://127.0.0.1:5000/`
- SerpAPI (Google Shopping): `http://127.0.0.1:5000/serpapi`

---

## Como usar

### Aba 1 — Compras.gov.br (CATMAT)

1. Acesse o [Catálogo de Compras](https://catalogo.compras.gov.br/cnbs-web/busca) e localize o código CATMAT
2. Digite o **código CATMAT**
3. Clique em **Buscar**
4. Visualize o **resumo estatístico** e a **tabela de registros**

### Aba 2 — SerpAPI (Google Shopping)

1. Digite um termo (ex.: “caneta”, “mouse sem fio logitech”)
2. Clique em **Buscar**
3. Visualize a tabela (título, preço e loja) e o resumo estatístico quando possível

> A SerpAPI é uma API externa e pode ter **limite de uso (ex.: 250 consultas)**, dependendo do plano/chave.

---

## Regras de limpeza (CATMAT)

O **CATMAT é genérico**. Para reduzir ruído e deixar os números mais consistentes, aplicamos uma limpeza automática em `src/core/cleaning.py`, incluindo:

- **Filtro por descrição**: remove termos típicos de “não é unitário” (ex.: kit, lote, combo, caixa, pacote, etc.)
- **Filtro por unidade**: prioriza unidade quando disponível (ex.: UN/UNIDADE)
- **Filtro por data**: prioriza registros mais recentes (ex.: últimos 24 meses)
- **Outliers**: corte relativo por mediana e IQR

> Mesmo com filtros, revise descrição/marca/unidade antes de usar os números em documentos formais.

---

## Arquitetura do projeto

- `app.py`: cria o Flask e registra os blueprints
- `src/routes/`
  - `compras.py`: rota `/` (CATMAT)
  - `serpapi.py`: rota `/serpapi` (SerpAPI)
- `src/services/`
  - `compras_gov.py`: consulta a API do Compras.gov.br e normaliza colunas
  - `serpapi_client.py`: cliente SerpAPI (lê chave do `.env`)
- `src/core/`
  - `cleaning.py`: regras de limpeza e cálculo de estatísticas
  - `formatting.py`: formatação de moeda
- `templates/`: UI (abas, tabela e cards)
- `static/`: CSS

---

## Tecnologias

| Tecnologia | Função |
|------------|--------|
| Python | Linguagem base |
| Flask | Aplicação web e rotas |
| Requests | Consumo de APIs |
| Pandas | Tratamento/tabulação (CATMAT) |
| python-dotenv | Leitura do `.env` |
| Bootstrap | Estilos e componentes de UI |

---

## Fonte de dados

**Compras.gov.br — Dados Abertos**

- Catálogo: `https://catalogo.compras.gov.br/cnbs-web/busca`
- APIs: `https://dadosabertos.compras.gov.br/`

**SerpAPI (Google Shopping)**

- Endpoint: `https://serpapi.com/search`

---

## Desenvolvedores

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/DevLucasFontoura" target="_blank">
        <img src="https://github.com/DevLucasFontoura.png" width="120" alt="Lucas Fontoura" style="border-radius: 50%"/><br/>
        <b>Lucas Fontoura</b>
      </a><br/>
      <sub>Desenvolvedor · <a href="https://github.com/DevLucasFontoura">@DevLucasFontoura</a></sub>
    </td>
  </tr>
</table>


