# ============================================================================
# INSTALADOR COMPLETO - SOFHIE IA
# Caminho do projeto: C:\sofhie-ia
#
# Este script:
#   1. Verifica se Python e Node.js estao instalados (com as versoes certas)
#   2. Cria o ambiente virtual Python e instala as dependencias
#   3. Instala as dependencias do Node.js (ponte do WhatsApp)
#   4. Cria o arquivo .env a partir do modelo, se ainda nao existir
#   5. Roda os testes automatizados - SE QUALQUER TESTE FALHAR, O INSTALADOR PARA
#   6. Faz um backup inicial do banco de dados (se ja existir)
#   7. Mostra um resumo final: o que passou, o que falhou, o que fazer a seguir
#
# Como rodar:
#   powershell -ExecutionPolicy Bypass -File "C:\sofhie-ia\instalar.ps1"
#
# ============================================================================

$ErrorActionPreference = "Stop"
$CaminhoProjeto = $PSScriptRoot
$LogInstalacao  = Join-Path $CaminhoProjeto "data\logs\instalacao.log"

function Escrever-Log {
    param([string]$Mensagem, [string]$Tipo = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $linha = "$timestamp | $Tipo | $Mensagem"
    Write-Host $linha
    Add-Content -Path $LogInstalacao -Value $linha -ErrorAction SilentlyContinue
}

function Parar-ComErro {
    param([string]$Mensagem)
    Escrever-Log $Mensagem "ERRO"
    Write-Host ""
    Write-Host "[X] INSTALACAO INTERROMPIDA. Veja o motivo exato acima." -ForegroundColor Red
    Write-Host "    Nada foi deixado pela metade de forma silenciosa - corrija o problema apontado e rode o instalador de novo." -ForegroundColor Red
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  INSTALADOR SOFHIE IA - INSTALACAO COMPLETA" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

# ---------- 0. Verificar se a pasta do projeto existe ----------
if (-not (Test-Path $CaminhoProjeto)) {
    Parar-ComErro "Pasta do projeto nao encontrada em: $CaminhoProjeto (confirme se voce extraiu o .zip exatamente nesse caminho)"
}
Set-Location $CaminhoProjeto
New-Item -ItemType Directory -Force -Path (Join-Path $CaminhoProjeto "data\logs") | Out-Null
Escrever-Log "Pasta do projeto encontrada: $CaminhoProjeto"

# ---------- 1. Verificar Python ----------
Write-Host ""
Write-Host "[1/7] Verificando Python..." -ForegroundColor Yellow
try {
    $versaoPython = (python --version) 2>&1
    Escrever-Log "Python encontrado: $versaoPython"
} catch {
    Parar-ComErro "Python nao foi encontrado no PATH. Instale o Python 3.10+ em https://www.python.org/downloads/ e marque a opcao 'Add Python to PATH' durante a instalacao."
}

$numeroVersao = [regex]::Match($versaoPython, '\d+\.\d+').Value
if ([version]$numeroVersao -lt [version]"3.10") {
    Parar-ComErro "Python $numeroVersao encontrado, mas a versao minima necessaria e 3.10. Atualize o Python e rode o instalador novamente."
}
Write-Host "    OK - $versaoPython" -ForegroundColor Green

# ---------- 2. Verificar Node.js ----------
Write-Host ""
Write-Host "[2/7] Verificando Node.js..." -ForegroundColor Yellow
try {
    $versaoNode = (node --version) 2>&1
    Escrever-Log "Node.js encontrado: $versaoNode"
} catch {
    Parar-ComErro "Node.js nao foi encontrado no PATH. Instale o Node.js 18+ (LTS) em https://nodejs.org/"
}
Write-Host "    OK - Node $versaoNode" -ForegroundColor Green

# ---------- 3. Ambiente virtual Python + dependencias ----------
Write-Host ""
Write-Host "[3/7] Configurando ambiente Python..." -ForegroundColor Yellow
if (-not (Test-Path (Join-Path $CaminhoProjeto "venv"))) {
    Escrever-Log "Criando ambiente virtual..."
    python -m venv venv
    if ($LASTEXITCODE -ne 0) { Parar-ComErro "Falha ao criar o ambiente virtual Python." }
} else {
    Escrever-Log "Ambiente virtual ja existe - reaproveitando."
}

& "$CaminhoProjeto\venv\Scripts\Activate.ps1"
Escrever-Log "Instalando dependencias Python (requirements.txt)..."

# No Windows, o pip recusa se auto-atualizar quando chamado direto como "pip install --upgrade pip"
# (o pip.exe fica "em uso" durante a propria execucao). O jeito correto e via "python -m pip".
# Isso tambem NAO e critico o suficiente para parar a instalacao se falhar por qualquer motivo.
python -m pip install --upgrade pip --quiet 2>$null

pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) { Parar-ComErro "Falha ao instalar dependencias Python. Veja o erro do pip acima." }
Write-Host "    OK - Dependencias Python instaladas" -ForegroundColor Green

# ---------- 4. Dependencias Node.js ----------
Write-Host ""
Write-Host "[4/7] Configurando ponte do WhatsApp (Node.js)..." -ForegroundColor Yellow
Set-Location (Join-Path $CaminhoProjeto "whatsapp-service")
npm install --silent
if ($LASTEXITCODE -ne 0) { Parar-ComErro "Falha ao instalar dependencias do Node.js (npm install). Veja o erro acima." }
Set-Location $CaminhoProjeto
Write-Host "    OK - Dependencias Node.js instaladas" -ForegroundColor Green

# ---------- 5. Arquivo .env ----------
Write-Host ""
Write-Host "[5/7] Verificando arquivo de configuracao (.env)..." -ForegroundColor Yellow
$caminhoEnv = Join-Path $CaminhoProjeto ".env"
if (-not (Test-Path $caminhoEnv)) {
    Copy-Item (Join-Path $CaminhoProjeto ".env.example") $caminhoEnv
    Write-Host "    AVISO - Arquivo .env criado a partir do modelo. VOCE PRECISA EDITA-LO com suas chaves reais" -ForegroundColor Yellow
    Write-Host "    antes de rodar o sistema (veja o MANUAL_INSTALACAO.md para o passo a passo)." -ForegroundColor Yellow
    Escrever-Log ".env criado a partir do .env.example - precisa ser preenchido pelo usuario" "AVISO"
} else {
    Write-Host "    OK - Arquivo .env ja existe - mantendo suas configuracoes atuais" -ForegroundColor Green
}

# ---------- 6. Backup do banco de dados (se ja existir de uma instalacao anterior) ----------
Write-Host ""
Write-Host "[6/7] Verificando backup do banco de dados..." -ForegroundColor Yellow
$caminhoDB = Join-Path $CaminhoProjeto "data\sofhie.db"
if (Test-Path $caminhoDB) {
    $pastaBackup = Join-Path $CaminhoProjeto "data\backups"
    New-Item -ItemType Directory -Force -Path $pastaBackup | Out-Null
    $nomeBackup = "sofhie_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
    Copy-Item $caminhoDB (Join-Path $pastaBackup $nomeBackup)
    Write-Host "    OK - Backup do banco existente salvo em: data\backups\$nomeBackup" -ForegroundColor Green
    Escrever-Log "Backup criado: $nomeBackup"
} else {
    Write-Host "    INFO - Nenhum banco de dados anterior encontrado - instalacao nova, sem necessidade de backup." -ForegroundColor Gray
}

# ---------- 7. Testes automatizados ----------
Write-Host ""
Write-Host "[7/7] Rodando testes automatizados..." -ForegroundColor Yellow
python -m pytest tests/ -v
if ($LASTEXITCODE -ne 0) {
    Parar-ComErro "Os testes automatizados FALHARAM. O sistema NAO deve ser colocado em uso ate os testes passarem. Revise a saida acima para ver exatamente qual teste falhou e por que."
}
Write-Host "    OK - Todos os testes automatizados passaram" -ForegroundColor Green

# ---------- Verificacao de sintaxe de todos os arquivos (varredura final) ----------
Write-Host ""
Write-Host "Varredura final de integridade dos arquivos..." -ForegroundColor Yellow
python -m py_compile src\*.py src\publicadores\*.py dashboard\app.py tests\*.py supervisor.py
if ($LASTEXITCODE -ne 0) { Parar-ComErro "Foi encontrado um erro de sintaxe em algum arquivo Python. A instalacao foi interrompida antes de colocar o sistema no ar." }

node --check whatsapp-service\index.js
if ($LASTEXITCODE -ne 0) { Parar-ComErro "Foi encontrado um erro de sintaxe no arquivo da ponte do WhatsApp (index.js)." }
Write-Host "    OK - Nenhum erro de sintaxe encontrado em nenhum arquivo" -ForegroundColor Green

# ---------- Resumo final ----------
Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  INSTALACAO CONCLUIDA COM SUCESSO" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

if ((Get-Content $caminhoEnv -Raw) -match "coloque_sua_chave") {
    Write-Host "AVISO: o arquivo .env ainda tem valores de exemplo (nao preenchidos)." -ForegroundColor Yellow
    Write-Host "O sistema NAO vai funcionar de verdade ate voce preencher as chaves reais." -ForegroundColor Yellow
    Write-Host "Abra: $caminhoEnv" -ForegroundColor Yellow
    Write-Host "Siga o MANUAL_INSTALACAO.md para saber exatamente o que colocar em cada campo." -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "OK - Arquivo .env ja parece preenchido com valores reais." -ForegroundColor Green
    Write-Host ""
}

Write-Host "PROXIMO PASSO - rodar o sistema:" -ForegroundColor Cyan
Write-Host "   cd `"$CaminhoProjeto`"" -ForegroundColor White
Write-Host "   venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "   python supervisor.py" -ForegroundColor White
Write-Host ""
Write-Host "Na primeira vez, um QR Code vai aparecer no terminal - escaneie com o WhatsApp da empresa" -ForegroundColor White
Write-Host "(Configuracoes > Aparelhos conectados > Conectar um aparelho)." -ForegroundColor White
Write-Host ""

Write-Host "Log completo desta instalacao salvo em:" -ForegroundColor Gray
Write-Host "   $LogInstalacao" -ForegroundColor Gray
Write-Host ""
