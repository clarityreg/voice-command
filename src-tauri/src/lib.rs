use std::sync::Mutex;

use tauri::Manager;

mod commands;
mod vocab;
mod whisper;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let whisper_state = Mutex::new(whisper::WhisperState::new());

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(whisper_state)
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            // Attempt eager model load if file exists (best-effort)
            let state = app.handle().state::<whisper::ManagedWhisperState>();
            let mut s = state.lock().unwrap();
            if s.model_exists() {
                match s.load_model() {
                    Ok(()) => log::info!("Whisper model loaded on startup"),
                    Err(e) => log::warn!("Failed to load whisper model on startup: {e}"),
                }
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::whisper_model_status,
            commands::download_whisper_model,
            commands::load_whisper_model,
            commands::transcribe_audio,
            vocab::get_custom_vocab,
            vocab::save_custom_vocab,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
