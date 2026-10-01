# Sofhie IA — Atendimento automatizado via WhatsApp com IA

Sistema de atendimento e publicação automatizada que roda **localmente**, usando camadas gratuitas de IA
(**Groq**, com **Gemini** como fallback). A persona de atendimento se chama **Sofhie**.

> **Status:** projeto funcional em evolução, desenvolvido em fases (núcleo → publicações → hardening).
> Leia a seção [Avisos e uso responsável](#avisos-e-uso-responsável) antes de usar.

## O que faz

**Atendimento (Fase 1)**
- Recebe mensagens do WhatsApp e responde com a persona Sofhie.
- Detecta quando um lead está pronto para fechamento, sinaliza no banco e **notifica o responsável** no WhatsApp pessoal.
- Envia um **relatório diário automático** às 20h.
- Aplica limites diários e atrasos "humanizados" para reduzir o risco de bloqueio.
- Guarda tudo em um banco local (SQLite), sem nuvem paga, e exibe um painel HTML local com o resumo do dia.

**Publicações programadas (Fase 2)**
- **Fila de conteúdo pronto**: o conteúdo é cadastrado com antecedência, na ordem de publicação, e o sistema publica no horário certo.
- WhatsApp status (8/dia), canal do WhatsApp (2/dia), Instagram via Graph API oficial (2/dia) e LinkedIn (1/dia).
- O LinkedIn ficou em 1 publicação/dia de propósito: volume alto automatizado é penalizado pela própria plataforma.

**Robustez (Fase 3)**
- Logs em arquivo com rotação, retry automático nas chamadas de IA e rede de segurança no núcleo
  (nenhum erro inesperado deixa o cliente sem resposta).
- **Supervisor** (`supervisor.py`) que sobe os 4 componentes e reinicia automaticamente o que cair;
  após 10+ quedas na mesma hora, para de insistir e registra o alerta nos logs.
- Testes automatizados das partes críticas (deduplicação de leads, ordem da fila, contadores do relatório).

## Arquitetura

```
WhatsApp ⇄ whatsapp-service (Node.js, Baileys) ⇄ src.main (Python) ⇄ Groq / Gemini
                                                      │
                          SQLite ◄────────────────────┤
                          dashboard (Flask, :5000) ◄──┤
                          scheduler (relatório 20h, fila de publicações) ─► Instagram · LinkedIn · Canal
```

## Estrutura

```
src/                     # núcleo em Python
├── main.py              # servidor de atendimento
├── persona.py           # persona Sofhie
├── ia_client.py         # Groq + fallback Gemini, com retry
├── antiban.py           # limites diários e delays
├── database.py          # SQLite: leads, fila, contadores
├── scheduler.py         # relatório diário e publicações
├── publicador.py        # orquestra a fila de publicações
├── publicadores/        # instagram.py · linkedin.py · whatsapp_canal.py
├── adicionar_conteudo.py, importar_csv.py, gerar_token_linkedin.py
whatsapp-service/        # ponte com o WhatsApp (Node.js)
dashboard/               # painel HTML local
tests/                   # pytest
supervisor.py            # sobe e mantém todos os processos
```

## Como rodar

**Pré-requisitos:** Python 3.10+ e Node.js 18+.

```bash
# 1. Núcleo Python
python -m venv venv
venv\Scripts\activate            # Windows  (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
# edite o .env com suas chaves (Groq, Gemini) e NUMERO_NOTIFICACAO_DONO

# 2. Ponte do WhatsApp
cd whatsapp-service && npm install && cd ..

# 3. Tudo de uma vez (recomendado)
python supervisor.py
```

Na primeira execução, escaneie o QR Code que aparecer no terminal da ponte do WhatsApp.
O painel fica em **http://localhost:5000**. Para parar tudo: `Ctrl+C`.

Modo manual (4 terminais): `python -m src.main` · `cd whatsapp-service && node index.js` ·
`python dashboard/app.py` · `python -m src.scheduler`.
Há também um guia mais detalhado em [`MANUAL_INSTALACAO.md`](MANUAL_INSTALACAO.md).

### Variáveis de ambiente

Todas estão documentadas em [`.env.example`](.env.example). **Nunca publique o `.env`.**
Para o LinkedIn, não preencha o token à mão: rode `python -m src.gerar_token_linkedin`.

## Base de conhecimento da Sofhie

O comportamento fixo da persona fica em `src/persona.py`. O conhecimento de negócio (catálogo, FAQ, regras) fica em
`conhecimento_catalogo.md`, que **não é versionado**. Para começar:

```bash
cp conhecimento_catalogo.exemplo.md conhecimento_catalogo.md   # Windows: copy
# edite com os dados reais e reinicie o supervisor
```

Sem o arquivo real, a Sofhie usa o modelo `conhecimento_catalogo.exemplo.md`. Não coloque nele segredos, margens ou dados de
outros clientes: o conteúdo pode ser repetido aos clientes.

## Publicações programadas

Adicionar um item por vez:

```bash
python -m src.adicionar_conteudo --canal whatsapp_status --tipo texto --texto "Sua mensagem"
python -m src.adicionar_conteudo --canal instagram --tipo imagem --texto "Legenda" --midia "URL_PUBLICA"
python -m src.adicionar_conteudo --canal linkedin --tipo artigo --texto "Texto do post"
```

Ou em massa, via CSV (modelo em [`modelo_conteudo.csv`](modelo_conteudo.csv)):

```bash
python -m src.importar_csv --arquivo meu_conteudo.csv
```

O arquivo inteiro é validado antes de qualquer importação: havendo erro, nada é importado e você recebe a lista exata
do que corrigir. **A ordem de cadastro é a ordem de publicação** dentro de cada canal.

## Testes

```bash
pytest tests/ -v
```

## Limitações conhecidas

- A publicação no **canal do WhatsApp** exige configurar o `CANAL_ID` em `whatsapp-service/index.js`
  (crie o canal pelo app do WhatsApp antes).
- A aprovação de apps no **LinkedIn Developer Portal** é um processo externo e pode levar alguns dias.

## Avisos e uso responsável

- **WhatsApp não oficial.** A conexão usa a biblioteca **Baileys**, que **não é oficial** e viola os Termos de Uso
  da Meta: o número pode ser bloqueado a qualquer momento, mesmo com os limites ativos
  (`LIMITE_NOVOS_CONTATOS_DIA`, `LIMITE_MENSAGENS_DIA`). Use apenas em um número que você possa perder.
  **Para produção, use a API oficial do WhatsApp Business Platform.**
- **Privacidade (LGPD).** O sistema armazena telefones e conversas de leads em um banco local. Informe os contatos,
  respeite pedidos de descadastro e não versione o banco nem as sessões do WhatsApp.
- **Segredos.** Chaves de API, tokens e a pasta de sessão do WhatsApp nunca devem ir para o repositório
  (o `.gitignore` já os cobre).

## Autor

**José Wagner Blanco Júnior** — [github.com/josewagnerbljr-sys](https://github.com/josewagnerbljr-sys)
