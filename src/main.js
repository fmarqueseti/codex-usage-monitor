import './styles.css';
import { invoke } from '@tauri-apps/api/core';
import { USAGE_REFRESH_INTERVAL_MS } from './config.js';

const app = document.querySelector('#app');
app.innerHTML = `<main class="shell"><header><div><span class="eyebrow">CODEX</span><h1>Usage Monitor</h1></div><button id="refresh">↻ Atualizar</button></header><p id="message" class="message">Carregando dados do Codex...</p><section class="cards" id="cards"></section></main>`;

let latest;
let countdownTimer;

function formatCountdown(seconds) {
  let value = Math.max(0, Math.floor(Number(seconds) || 0));
  const days = Math.floor(value / 86400);
  value %= 86400;
  const hours = Math.floor(value / 3600);
  value %= 3600;
  const minutes = Math.floor(value / 60);
  const secs = value % 60;
  if (days) return `${days}d ${String(hours).padStart(2, '0')}h ${String(minutes).padStart(2, '0')}m`;
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function level(percent) {
  if (percent === 0) return 'exhausted';
  if (percent < 10) return 'danger';
  if (percent < 25) return 'critical';
  if (percent < 50) return 'warning';
  return 'normal';
}

function render(data) {
  document.querySelector('#cards').innerHTML = ['five_hour', 'weekly'].map((key) => {
    const item = data[key];
    const remaining = Math.max(0, Math.min(100, Number(item.remaining_percent)));
    return `<article class="card ${level(remaining)}"><h2>${item.name}</h2><div class="bar" aria-label="${remaining}% disponível"><i style="width:${remaining}%"></i></div><strong>${remaining}% available</strong><p>Used: ${item.used_percent}%<br>Reset: ${item.reset_text || '—'}<br><span class="countdown">⏱ ${formatCountdown(item.seconds_until_reset)}</span></p></article>`;
  }).join('');
}

function startCountdown() {
  clearInterval(countdownTimer);
  countdownTimer = setInterval(() => {
    if (!latest) return;
    latest.five_hour.seconds_until_reset = Math.max(0, latest.five_hour.seconds_until_reset - 1);
    latest.weekly.seconds_until_reset = Math.max(0, latest.weekly.seconds_until_reset - 1);
    document.querySelectorAll('.countdown').forEach((element, index) => {
      const item = latest[index === 0 ? 'five_hour' : 'weekly'];
      element.textContent = `⏱ ${formatCountdown(item.seconds_until_reset)}`;
    });
    if (latest.five_hour.seconds_until_reset === 0 || latest.weekly.seconds_until_reset === 0) load();
  }, 1000);
}

async function load() {
  const message = document.querySelector('#message');
  message.textContent = 'Consultando o App Server do Codex...';
  try {
    const snapshot = await invoke('get_usage');
    latest = structuredClone(snapshot);
    render(latest);
    message.textContent = `Fonte: ${latest.source} · Atualizado: ${new Date(latest.captured_at).toLocaleTimeString()}`;
    startCountdown();
  } catch (error) {
    message.textContent = `⚠ Não foi possível consultar o Codex. Motivo: ${error}`;
  }
}

document.querySelector('#refresh').addEventListener('click', load);
setInterval(load, USAGE_REFRESH_INTERVAL_MS);
load();
