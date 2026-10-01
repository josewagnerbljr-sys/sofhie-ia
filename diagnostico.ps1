# ============================================================================
# DIAGNOSTICO SOFHIE IA
# Verifica CADA componente individualmente e diz exatamente o que esta
# funcionando e o que nao esta - sem suposicoes, testando de verdade.
#
# Como rodar:
#   powershell -ExecutionPolicy Bypass -File "C:\sofhie-ia\diagnostico.ps1"
# ============================================================================

$CaminhoProjeto = $PSScriptRoot
Set-Location $CaminhoProjeto

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  DIAGNOSTICO SOFHIE IA" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

$problemas = @()

function Testar {
    param([string]$Nome, [scriptblock]$Verificacao)
    Write-Host -NoNewline "  $Nome... "
    try {
        $resultado = & $Verificacao
        if ($resultado -eq $true) {
            Write-Host "OK" -ForegroundColor Green
        } else {
            Write-Host "FALHOU - $resultado" -ForegroundColor Red
            $script:problemas += "$Nome`: $resultado"
        }
    } catch {
        Write-Host "FALHOU - $($_.Exception.Message)" -ForegroundColor Red
        $script:problemas += "$Nome`: $($_.Exception.Message)"
    }
}

Write-Host "1. Arquivos e configuracao" -ForegroundColor Yellow
Testar "Pasta do projeto existe" { Test-Path $CaminhoProjeto }
Testar "Ambiente virtual Python existe" { Test-Path (Join-Path $CaminhoProjeto "venv\Scripts\python.exe") }
Testar "Dependencias Node.js instaladas" { Test-Path (Join-Path $CaminhoProjeto "whatsapp-service\node_modules") }
Testar "Arquivo .env existe" { Test-Path (Join-Path $CaminhoProjeto ".env") }

$caminhoEnv = Join-Path $CaminhoProjeto ".env"
if (Test-Path $caminhoEnv) {
    $conteudoEnv = Get-Content $caminhoEnv -Raw
    Testar "GROQ_API_KEY preenchida (nao e o valor de exemplo)" {
        if ($conteudoEnv -match "GROQ_API_KEY=coloque_sua_chave") { "ainda esta com o valor de exemplo - edite o .env" }
        elseif ($conteudoEnv -notmatch "GROQ_API_KEY=.+") { "linha nao encontrada no .env" }
        else { $true }
    }
    Testar "NUMERO_NOTIFICACAO_DONO preenchido" {
        if ($conteudoEnv -match "NUMERO_NOTIFICACAO_DONO=5500000000000") { "ainda esta com o valor de exemplo - edite o .env" }
        else { $true }
    }
}

Write-Host ""
Write-Host "2. Processos em execucao" -ForegroundColor Yellow
$portas = @{ "Nucleo Python (porta 8000)" = 8000; "Ponte WhatsApp (porta 8001)" = 8001; "Dashboard (porta 5000)" = 5000 }
foreach ($nome in $portas.Keys) {
    $porta = $portas[$nome]
    Testar $nome {
        $conexao = Get-NetTCPConnection -LocalPort $porta -State Listen -ErrorAction SilentlyContinue
        if ($conexao) { $true } else { "nada rodando nessa porta - o processo nao esta de pe" }
    }
}

Write-Host ""
Write-Host "3. Resposta real dos servicos (nao so a porta aberta)" -ForegroundColor Yellow
Testar "Nucleo Python responde (/saude)" {
    try {
        $r = Invoke-RestMethod -Uri "http://localhost:8000/saude" -TimeoutSec 5
        if ($r.status -eq "ok") { $true } else { "respondeu, mas com status inesperado: $($r.status)" }
    } catch { "nao respondeu - verifique se 'python supervisor.py' esta rodando" }
}
Testar "Ponte WhatsApp responde (/saude)" {
    try {
        $r = Invoke-RestMethod -Uri "http://localhost:8001/saude" -TimeoutSec 5
        if ($r.whatsapp_conectado -eq $true) { $true }
        else { "servico no ar, mas o WhatsApp ainda NAO esta conectado - escaneie o QR Code no terminal" }
    } catch { "nao respondeu - verifique se o Node.js (whatsapp-service) esta rodando" }
}
Testar "Dashboard responde" {
    try {
        Invoke-WebRequest -Uri "http://localhost:5000" -TimeoutSec 5 -UseBasicParsing | Out-Null
        $true
    } catch { "nao respondeu - verifique se o dashboard esta rodando" }
}

Write-Host ""
Write-Host "4. Banco de dados" -ForegroundColor Yellow
Testar "Arquivo do banco existe" { Test-Path (Join-Path $CaminhoProjeto "data\sofhie.db") }

Write-Host ""
Write-Host "5. Ultimos erros nos logs (se houver)" -ForegroundColor Yellow
$pastaLogs = Join-Path $CaminhoProjeto "data\logs"
if (Test-Path $pastaLogs) {
    $arquivosLog = Get-ChildItem $pastaLogs -Filter "*.log"
    foreach ($arquivo in $arquivosLog) {
        $ultimosErros = Get-Content $arquivo.FullName -Tail 200 | Select-String "ERROR|CRITICAL" | Select-Object -Last 3
        if ($ultimosErros) {
            Write-Host "  AVISO - $($arquivo.Name) - ultimos erros encontrados:" -ForegroundColor Yellow
            foreach ($linha in $ultimosErros) { Write-Host "     $linha" -ForegroundColor DarkYellow }
        }
    }
} else {
    Write-Host "  Nenhum log ainda - o sistema provavelmente nunca foi executado." -ForegroundColor Gray
}

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
if ($problemas.Count -eq 0) {
    Write-Host "  RESULTADO: tudo funcionando corretamente." -ForegroundColor Green
} else {
    Write-Host "  RESULTADO: $($problemas.Count) problema(s) encontrado(s):" -ForegroundColor Red
    foreach ($p in $problemas) { Write-Host "   - $p" -ForegroundColor Red }
}
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""
