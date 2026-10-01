/**
 * Ponte WhatsApp <-> Python (Sofhie IA)
 *
 * Este serviço:
 * 1. Conecta ao WhatsApp via QR Code (biblioteca Baileys, não-oficial).
 * 2. Ao receber mensagem de um cliente, encaminha para o núcleo Python (porta 8000).
 * 3. Recebe de volta a resposta gerada pela IA e envia ao cliente no WhatsApp.
 *
 * IMPORTANTE: automação via Baileys não é o método oficial do WhatsApp e viola os
 * Termos de Uso da Meta. O número pode ser bloqueado a qualquer momento, mesmo com
 * as proteções anti-ban ativas. Use um número dedicado sempre que possível.
 */
const express = require("express");
const qrcode = require("qrcode-terminal");
const pino = require("pino");
const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
} = require("@whiskeysockets/baileys");

// Logger mais silencioso — o padrao do Baileys (nivel "info") inunda o terminal
// com centenas de linhas por segundo durante a sincronizacao inicial, o que
// alem de dificultar o uso tambem consome CPU extra em hardware mais antigo.
const logger = pino({ level: "warn" });

const PYTHON_CORE_URL = "http://localhost:8000/mensagem-recebida";
const PORTA_LOCAL = 8001;

let sock;
let conexaoPronta = false;

async function iniciarConexao() {
  const { state, saveCreds } = await useMultiFileAuthState("auth_sessao");

  sock = makeWASocket({
    auth: state,
    printQRInTerminal: false,
    logger,
    // Desativa o download completo do historico de conversas. A Sofhie so
    // precisa de mensagens NOVAS a partir de agora — sincronizar anos de
    // historico consome muito CPU/banda e e desnecessario para o atendimento.
    // Isso tambem reduz a quantidade de dados sensiveis (conversas antigas)
    // que ficam armazenados localmente pela ponte.
    syncFullHistory: false,
    shouldSyncHistoryMessage: () => false,
  });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect, qr } = update;
    if (qr) {
      console.log("\n=== Escaneie o QR Code abaixo com o WhatsApp da empresa ===\n");
      qrcode.generate(qr, { small: true });
    }
    if (connection === "close") {
      conexaoPronta = false;
      const deveReconectar =
        lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut;
      console.log("Conexão encerrada. Reconectar?", deveReconectar);
      if (deveReconectar) iniciarConexao();
    } else if (connection === "open") {
      conexaoPronta = true;
      console.log("✅ Conectado ao WhatsApp com sucesso.");
    }
  });

  sock.ev.on("messages.upsert", async ({ messages }) => {
    const msg = messages[0];
    if (!msg.message || msg.key.fromMe) return;

    // Ignora atualizacoes de Status (stories) de outros contatos — nao sao
    // mensagens de clientes reais, e trata-las como tal desperdicaria chamadas
    // da API de IA e criaria leads falsos no banco.
    if (msg.key.remoteJid === "status@broadcast") return;

    const telefone = msg.key.remoteJid;
    const texto =
      msg.message.conversation ||
      msg.message.extendedTextMessage?.text ||
      "";

    if (!texto) return;

    console.log(`[BRIDGE] Mensagem recebida de ${telefone} — encaminhando para o nucleo...`);

    try {
      const resposta = await fetch(PYTHON_CORE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ telefone, mensagem: texto }),
      });
      const dados = await resposta.json();

      if (dados.resposta) {
        console.log(`[BRIDGE] Resposta pronta, aguardando ${dados.delay_ms || 2000}ms antes de enviar...`);
        await sock.sendPresenceUpdate("composing", telefone);
        await new Promise((r) => setTimeout(r, dados.delay_ms || 2000));
        await sock.sendMessage(telefone, { text: dados.resposta });
        console.log(`[BRIDGE] Resposta enviada para ${telefone}.`);
      } else {
        console.log(`[BRIDGE] Nucleo nao retornou resposta (provavelmente limite diario atingido).`);
      }
    } catch (erro) {
      console.error("[BRIDGE] Erro ao encaminhar mensagem para o nucleo Python:", erro.message);
    }
  });
}

// Endpoint simples para o Python publicar um status, se precisar acionar por aqui
const app = express();
app.use(express.json());

app.post("/publicar-status", async (req, res) => {
  if (!conexaoPronta) {
    return res.status(503).json({ ok: false, erro: "WhatsApp ainda conectando ou desconectado — tente novamente em instantes." });
  }
  try {
    const { texto } = req.body;
    await sock.updateProfileStatus(texto);
    res.json({ ok: true });
  } catch (erro) {
    res.status(500).json({ ok: false, erro: erro.message });
  }
});

// Endpoint genérico de envio — usado para notificar o dono do número (leads prontos,
// relatório diário, alertas) e futuramente para as publicações programadas.
app.post("/enviar-mensagem", async (req, res) => {
  if (!conexaoPronta) {
    return res.status(503).json({ ok: false, erro: "WhatsApp ainda conectando ou desconectado — tente novamente em instantes." });
  }
  try {
    const { telefone, texto } = req.body;
    if (!telefone || !texto) {
      return res.status(400).json({ ok: false, erro: "telefone e texto são obrigatórios" });
    }
    await sock.sendMessage(telefone, { text: texto });
    res.json({ ok: true });
  } catch (erro) {
    res.status(500).json({ ok: false, erro: erro.message });
  }
});

// Publicação em Canal do WhatsApp (WhatsApp Channel / newsletter).
// Suporte a canais no Baileys é experimental — CANAL_ID precisa ser preenchido
// manualmente aqui após você criar o canal pelo próprio app do WhatsApp.
const CANAL_ID = ""; // ex: "120363012345678901@newsletter"

app.post("/publicar-canal", async (req, res) => {
  if (!conexaoPronta) {
    return res.status(503).json({ ok: false, erro: "WhatsApp ainda conectando ou desconectado — tente novamente em instantes." });
  }
  try {
    if (!CANAL_ID) {
      return res.status(400).json({
        ok: false,
        erro: "CANAL_ID não configurado no index.js — crie o canal no WhatsApp e cole o ID aqui.",
      });
    }
    const { texto } = req.body;
    await sock.sendMessage(CANAL_ID, { text: texto });
    res.json({ ok: true });
  } catch (erro) {
    res.status(500).json({ ok: false, erro: erro.message });
  }
});

// Endpoint de saúde — usado pelo instalador/testes para confirmar que a ponte subiu.
app.get("/saude", (req, res) => {
  res.json({ status: "ok", whatsapp_conectado: conexaoPronta });
});

app.listen(PORTA_LOCAL, () => {
  console.log(`Ponte WhatsApp rodando em http://localhost:${PORTA_LOCAL}`);
});

iniciarConexao();
