use futures_util::StreamExt;
use serde::Serialize;
use tauri::{AppHandle, Emitter, State};

use crate::whisper::{self, ManagedWhisperState};

#[derive(Serialize)]
pub struct ModelStatus {
    pub model_exists: bool,
    pub model_loaded: bool,
    pub model_path: String,
}

#[derive(Clone, Serialize)]
pub struct DownloadProgress {
    pub downloaded: u64,
    pub total: u64,
    pub percent: f64,
}

#[tauri::command]
pub fn whisper_model_status(state: State<'_, ManagedWhisperState>) -> ModelStatus {
    let s = state.lock().unwrap();
    ModelStatus {
        model_exists: s.model_exists(),
        model_loaded: s.is_loaded(),
        model_path: s.model_path().to_string_lossy().to_string(),
    }
}

const MODEL_URLS: &[(&str, &str)] = &[
    (
        "small.en",
        "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin",
    ),
    (
        "base.en",
        "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin",
    ),
];

#[tauri::command]
pub async fn download_whisper_model(
    app: AppHandle,
    state: State<'_, ManagedWhisperState>,
    model_name: Option<String>,
) -> Result<String, String> {
    let name = model_name.as_deref().unwrap_or("small.en");
    let url = MODEL_URLS
        .iter()
        .find(|(n, _)| *n == name)
        .map(|(_, u)| *u)
        .ok_or_else(|| format!("Unknown model: {name}. Available: small.en, base.en"))?;

    let filename = format!("ggml-{name}.bin");
    let model_dir = {
        let s = state.lock().unwrap();
        s.model_path().parent().unwrap().to_path_buf()
    };

    tokio::fs::create_dir_all(&model_dir)
        .await
        .map_err(|e| format!("Failed to create model directory: {e}"))?;

    let dest = model_dir.join(&filename);

    let response = reqwest::get(url)
        .await
        .map_err(|e| format!("Download request failed: {e}"))?;

    if !response.status().is_success() {
        return Err(format!("Download failed with status: {}", response.status()));
    }

    let total = response.content_length().unwrap_or(0);
    let mut downloaded: u64 = 0;

    let tmp_path = dest.with_extension("bin.tmp");
    let mut file = tokio::fs::File::create(&tmp_path)
        .await
        .map_err(|e| format!("Failed to create file: {e}"))?;

    let mut stream = response.bytes_stream();
    use tokio::io::AsyncWriteExt;

    while let Some(chunk) = stream.next().await {
        let chunk = chunk.map_err(|e| format!("Download stream error: {e}"))?;
        file.write_all(&chunk)
            .await
            .map_err(|e| format!("File write error: {e}"))?;

        downloaded += chunk.len() as u64;
        let percent = if total > 0 {
            (downloaded as f64 / total as f64) * 100.0
        } else {
            0.0
        };

        let _ = app.emit(
            "whisper-download-progress",
            DownloadProgress {
                downloaded,
                total,
                percent,
            },
        );
    }

    file.flush()
        .await
        .map_err(|e| format!("File flush error: {e}"))?;
    drop(file);

    tokio::fs::rename(&tmp_path, &dest)
        .await
        .map_err(|e| format!("Failed to move downloaded file: {e}"))?;

    // Update state model path if a different model was chosen
    {
        let mut s = state.lock().unwrap();
        s.set_model_path(dest.clone());
    }

    Ok(dest.to_string_lossy().to_string())
}

#[tauri::command]
pub fn load_whisper_model(state: State<'_, ManagedWhisperState>) -> Result<(), String> {
    let mut s = state.lock().unwrap();
    s.load_model()
}

#[tauri::command]
pub fn transcribe_audio(
    audio_data: Vec<u8>,
    sample_rate: u32,
    state: State<'_, ManagedWhisperState>,
) -> Result<String, String> {
    let samples_f32 = whisper::pcm_i16le_to_f32(&audio_data);
    let resampled = whisper::resample_to_16khz(&samples_f32, sample_rate);

    // Load vocab terms for initial prompt
    let vocab_path = dirs::home_dir()
        .unwrap_or_default()
        .join(".clarity")
        .join("whisper-vocab.txt");
    let vocab_terms = if vocab_path.exists() {
        std::fs::read_to_string(&vocab_path)
            .unwrap_or_default()
            .lines()
            .map(|l| l.trim().to_string())
            .filter(|l| !l.is_empty())
            .collect()
    } else {
        Vec::new()
    };

    let s = state.lock().unwrap();
    s.transcribe(&resampled, &vocab_terms)
}
