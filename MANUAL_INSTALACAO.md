# Manual de Instalação e Integração — Sofhie IA

Este manual cobre tudo que você precisa fazer, do zero, para colocar o sistema
no ar de verdade: instalação, onde colocar cada chave, e como integrar com
WhatsApp, Instagram e LinkedIn.

Caminho do projeto neste manual: `C:\sofhie-ia`

---

## 1. Pré-requisitos (instale ANTES de rodar o instalador)

| Programa | Versão mínima | Onde baixar |
|---|---|---|
| Python | 3.10+ | https://www.python.org/downloads/ — **marque "Add Python to PATH"** durante a instalação |
| Node.js | 18+ (LTS) | https://nodejs.org/ |

Para confirmar que instalou certo, abra o PowerShell e rode:
```
python --version
node --version
```
Se qualquer um desses comandos der erro de "não reconhecido", reinstale marcando a opção de adicionar ao PATH.

---

## 2. Rodando o instalador

Abra o PowerShell nesse caminho e rode:
```
powershell -ExecutionPolicy Bypass -File "C:\sofhie-ia\instalar.ps1"
```

O instalador faz tudo sozinho: cria o ambiente Python, instala as dependências,
prepara o Node.js, cria o `.env`, roda os testes automatizados e faz backup se
já existir um banco de dados anterior. **Se qualquer teste falhar, o instalador
para imediatamente** e mostra exatamente o que falhou — ele não deixa o sistema
"pela metade" silenciosamente.

---

## 3. Onde colocar cada chave (arquivo `.env`)

Depois de instalar, abra o arquivo `.env` (criado automaticamente na pasta do
projeto) com o Bloco de Notas ou VS Code e preencha:

### 3.1 Groq (obrigatório — é o "cérebro" principal da Sofhie)
1. Acesse **console.groq.com** e faça login (grátis, sem cartão)
2. Vá em **API Keys** → **Create API Key**
3. Copie a chave gerada e cole em:
   ```
   GROQ_API_KEY=cole_aqui_a_chave_gerada
   ```

### 3.2 Gemini (fallback — usado só se a Groq falhar)
1. Acesse **aistudio.google.com/app/apikey**
2. Clique em **Create API Key** (grátis)
3. Cole em:
   ```
   GEMINI_API_KEY=cole_aqui_a_chave_gerada
   ```

### 3.3 Seu número pessoal (notificações)
Formato: código do país + DDD + número, sem espaços, seguido de `@s.whatsapp.net`
```
NUMERO_NOTIFICACAO_DONO=5544912345678@s.whatsapp.net
```

### 3.4 Instagram (API oficial — Graph API)
Pré-requisito: sua conta Instagram precisa ser **Profissional** e estar vinculada
a uma **Página do Facebook**.

1. Acesse **developers.facebook.com** → crie um app do tipo "Empresa"
2. No painel do app, adicione o produto **Instagram Graph API**
3. Gere um **token de acesso de usuário** com as permissões:
   `instagram_basic`, `instagram_content_publish`, `pages_read_engagement`
4. Troque esse token por um **token de longa duração** (dura ~60 dias, renovável) —
   a própria documentação da Meta explica o passo de troca via endpoint `/oauth/access_token`
5. Pegue o **ID da conta Business do Instagram** (aparece no Graph API Explorer
   consultando `/me/accounts` e depois o campo `instagram_business_account`)
6. Preencha:
   ```
   INSTAGRAM_ACCESS_TOKEN=cole_aqui_o_token_de_longa_duracao
   INSTAGRAM_BUSINESS_ACCOUNT_ID=cole_aqui_o_id_da_conta
   ```

⚠️ O token de longa duração expira e precisa ser renovado periodicamente — isso é
regra da própria Meta, não uma limitação do sistema.

### 3.5 LinkedIn (API oficial)
1. Acesse **linkedin.com/developers** → **Create App**
2. Vincule o app à sua **Página de Empresa** do LinkedIn
3. Solicite acesso ao produto **"Share on LinkedIn"** (ou "Community Management API")
   — **esse processo passa por aprovação manual do LinkedIn e pode levar alguns dias**,
   isso não depende do sistema nem de mim
4. Depois de aprovado, gere o **token de acesso** OAuth 2.0
5. Pegue o **URN da sua organização** (formato `urn:li:organization:123456`)
6. Preencha:
   ```
   LINKEDIN_ACCESS_TOKEN=cole_aqui_o_token
   LINKEDIN_ORGANIZATION_URN=urn:li:organization:seu_id_aqui
   ```

### 3.6 WhatsApp (conexão via QR Code — não precisa de chave)
Não tem chave para configurar aqui. Na primeira vez que você rodar o sistema
(`python supervisor.py`), um **QR Code vai aparecer direto no terminal**. Abra o
WhatsApp da empresa no celular → **Configurações → Aparelhos conectados →
Conectar um aparelho** → escaneie o QR Code.

### 3.7 Canal do WhatsApp (opcional, para publicações no canal)
1. Crie o canal pelo próprio app do WhatsApp, se ainda não tiver um
2. O ID do canal precisa ser copiado manualmente e colado no arquivo
   `whatsapp-service\index.js`, na linha:
   ```js
   const CANAL_ID = ""; // cole o ID do seu canal aqui, ex: "120363012345678901@newsletter"
   ```
   (o jeito mais confiável de pegar esse ID é me avisar depois de criar o canal —
   dá para extrair automaticamente com um pequeno ajuste no código)

---

## 4. Rodando o sistema no dia a dia

Modo recomendado (1 comando, com reinício automático em caso de falha):
```
cd "C:\sofhie-ia"
venv\Scripts\Activate.ps1
python supervisor.py
```

Para checar se está tudo saudável a qualquer momento, sem precisar adivinhar:
```
powershell -ExecutionPolicy Bypass -File "C:\sofhie-ia\diagnostico.ps1"
```
Esse script testa cada componente de verdade (não só "parece que está rodando") e
te diz exatamente qual parte está com problema, se houver.

---

## 5. Alimentando e treinando a Sofhie

### 5.1 Ajustar a personalidade
Edite `src\persona.py` — é o texto que define como a Sofhie fala, o que ela pode
e não pode fazer. Depois de editar, reinicie o núcleo (`Ctrl+C` no supervisor e
rode `python supervisor.py` de novo) para a mudança valer.

### 5.2 Alimentar a fila de publicações
Um item por vez:
```
python -m src.adicionar_conteudo --canal whatsapp_status --tipo texto --texto "Sua mensagem"
```
Em massa via CSV (recomendado):
```
python -m src.importar_csv --arquivo modelo_conteudo.csv
```

### 5.3 Acompanhar tudo
- Dashboard: **http://localhost:5000**
- Relatório diário automático: chega no seu WhatsApp pessoal às 20h
- Notificação de lead pronto: chega em tempo real, assim que acontece

---

## 6. Backups

- **Automático diário**, às 3h da manhã — mantém os últimos 14 dias, em
  `data\backups\`
- **No momento da instalação/reinstalação**, o instalador já faz um backup
  extra do banco existente antes de qualquer alteração

Para restaurar um backup manualmente: pare o sistema, copie o arquivo desejado
de `data\backups\` para `data\sofhie.db` (substituindo o atual), e reinicie.

---

## 7. Em caso de problema

1. Rode o `diagnostico.ps1` (seção 4 acima) — ele aponta exatamente onde está o problema
2. Veja os logs detalhados em `data\logs\` (um arquivo por componente)
3. Me traga a saída do diagnóstico — a partir dela eu já sei exatamente o que corrigir,
   sem precisarmos adivinhar juntos
