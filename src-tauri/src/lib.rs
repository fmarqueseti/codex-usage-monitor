use chrono::{Local, Utc};
use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Write};
use std::process::{Command, Stdio};

#[tauri::command]
fn get_usage() -> Result<Value, String> {
    let command = std::env::var("CODEX_COMMAND").unwrap_or_else(|_| "codex".into());
    let mut child = Command::new(command).args(["app-server", "--stdio"])
        .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null())
        .spawn().map_err(|e| format!("não foi possível iniciar o App Server: {e}"))?;
    let result = (|| {
        let mut input = child.stdin.take().ok_or("stdin indisponível")?;
        let mut reader = BufReader::new(child.stdout.take().ok_or("stdout indisponível")?);
        let init = json!({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"clientInfo":{"name":"codex-usage-monitor","version":"0.1.0"},"capabilities":{}}});
        writeln!(input, "{init}").map_err(|e| e.to_string())?;
        read_response(&mut reader, 1)?;
        let initialized = json!({"jsonrpc":"2.0","method":"initialized","params":{}});
        writeln!(input, "{initialized}").map_err(|e| e.to_string())?;
        let request = json!({"jsonrpc":"2.0","id":2,"method":"account/rateLimits/read","params":{"excludeResetCreditDetails":true}});
        writeln!(input, "{request}").map_err(|e| e.to_string())?;
        let response = read_response(&mut reader, 2)?;
        if let Some(error) = response.get("error") { return Err(format!("App Server retornou erro: {error}")); }
        normalize(response.get("result").ok_or("resposta sem result")?)
    })();
    let _ = child.kill();
    result
}

fn read_response(reader: &mut BufReader<impl std::io::Read>, id: i64) -> Result<Value, String> {
    let mut line = String::new();
    loop {
        line.clear();
        if reader.read_line(&mut line).map_err(|e| e.to_string())? == 0 { return Err("App Server encerrou sem resposta".into()); }
        if line.trim().is_empty() { continue; }
        let message: Value = serde_json::from_str(&line).map_err(|e| format!("resposta inválida do App Server: {e}"))?;
        if message.get("id").and_then(Value::as_i64) == Some(id) { return Ok(message); }
    }
}

fn normalize(result: &Value) -> Result<Value, String> {
    let snapshots = result.get("rateLimitsByLimitId").and_then(|v| v.get("codex"))
        .unwrap_or_else(|| result.get("rateLimits").unwrap_or(&Value::Null));
    let mut windows: Vec<&Value> = ["primary", "secondary"].iter().filter_map(|key| snapshots.get(key))
        .filter(|w| w.get("resetsAt").and_then(Value::as_i64).is_some() && w.get("usedPercent").and_then(Value::as_i64).is_some()).collect();
    windows.sort_by_key(|w| w.get("windowDurationMins").and_then(Value::as_i64).unwrap_or(0));
    if windows.len() < 2 { return Err("resposta não contém as janelas 5h e Weekly".into()); }
    let now = Utc::now();
    let make_window = |name: &str, w: &Value| -> Result<Value, String> {
        let used = w["usedPercent"].as_i64().ok_or("usedPercent inválido")?.clamp(0, 100);
        let reset_epoch = w["resetsAt"].as_i64().ok_or("resetsAt inválido")?;
        let reset = chrono::DateTime::from_timestamp(reset_epoch, 0).ok_or("resetsAt inválido")?.with_timezone(&Local);
        let remaining = 100 - used;
        Ok(json!({"name":name,"remaining_percent":remaining,"used_percent":used,"reset_text":reset.format("%H:%M on %-d %b").to_string(),"reset_at":reset.to_rfc3339(),"seconds_until_reset":(reset.with_timezone(&Utc)-now).num_seconds().max(0)}))
    };
    Ok(json!({"source":"codex app-server account/rateLimits/read","captured_at":now.with_timezone(&Local).to_rfc3339(),"five_hour":make_window("5-hour",windows[0])?,"weekly":make_window("Weekly",windows[1])?}))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default().plugin(tauri_plugin_opener::init()).invoke_handler(tauri::generate_handler![get_usage]).run(tauri::generate_context!()).expect("error while running Codex Usage Monitor");
}
