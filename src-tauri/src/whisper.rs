use std::path::PathBuf;
use std::sync::Mutex;

use whisper_rs::{FullParams, SamplingStrategy, WhisperContext, WhisperContextParameters};

use crate::vocab;

pub struct WhisperState {
    context: Option<WhisperContext>,
    model_path: PathBuf,
}

impl WhisperState {
    pub fn new() -> Self {
        let model_dir = dirs::home_dir()
            .unwrap_or_default()
            .join(".clarity")
            .join("models");
        Self {
            context: None,
            model_path: model_dir.join("ggml-small.en.bin"),
        }
    }

    pub fn model_path(&self) -> &PathBuf {
        &self.model_path
    }

    pub fn set_model_path(&mut self, path: PathBuf) {
        self.model_path = path;
    }

    pub fn model_exists(&self) -> bool {
        self.model_path.exists()
    }

    pub fn is_loaded(&self) -> bool {
        self.context.is_some()
    }

    pub fn load_model(&mut self) -> Result<(), String> {
        if !self.model_exists() {
            return Err(format!(
                "Model file not found: {}",
                self.model_path.display()
            ));
        }

        let ctx = WhisperContext::new_with_params(
            self.model_path.to_str().ok_or("Invalid model path")?,
            WhisperContextParameters::default(),
        )
        .map_err(|e| format!("Failed to load whisper model: {e}"))?;

        self.context = Some(ctx);
        Ok(())
    }

    pub fn transcribe(&self, audio: &[f32], vocab_terms: &[String]) -> Result<String, String> {
        let ctx = self
            .context
            .as_ref()
            .ok_or("Model not loaded")?;

        let mut state = ctx.create_state().map_err(|e| format!("Failed to create state: {e}"))?;

        let mut params = FullParams::new(SamplingStrategy::Greedy { best_of: 1 });
        params.set_language(Some("en"));
        params.set_print_progress(false);
        params.set_print_realtime(false);
        params.set_print_timestamps(false);
        params.set_single_segment(true);
        params.set_no_context(true);

        if !vocab_terms.is_empty() {
            let prompt = vocab::compose_initial_prompt(vocab_terms);
            params.set_initial_prompt(&prompt);
        }

        state
            .full(params, audio)
            .map_err(|e| format!("Transcription failed: {e}"))?;

        let num_segments = state.full_n_segments();
        let mut text = String::new();
        for i in 0..num_segments {
            if let Some(segment) = state.get_segment(i) {
                if let Ok(s) = segment.to_str_lossy() {
                    text.push_str(&s);
                }
            }
        }

        Ok(text.trim().to_string())
    }
}

pub type ManagedWhisperState = Mutex<WhisperState>;

/// Resample audio from source sample rate to 16kHz (what whisper expects).
pub fn resample_to_16khz(samples: &[f32], source_rate: u32) -> Vec<f32> {
    if source_rate == 16000 {
        return samples.to_vec();
    }

    let ratio = source_rate as f64 / 16000.0;
    let output_len = (samples.len() as f64 / ratio).ceil() as usize;
    let mut output = Vec::with_capacity(output_len);

    for i in 0..output_len {
        let src_idx = i as f64 * ratio;
        let idx = src_idx.floor() as usize;
        let frac = src_idx - idx as f64;

        let sample = if idx + 1 < samples.len() {
            samples[idx] as f64 * (1.0 - frac) + samples[idx + 1] as f64 * frac
        } else if idx < samples.len() {
            samples[idx] as f64
        } else {
            0.0
        };

        output.push(sample as f32);
    }

    output
}

/// Convert PCM i16 little-endian bytes to f32 samples normalized to [-1.0, 1.0].
pub fn pcm_i16le_to_f32(bytes: &[u8]) -> Vec<f32> {
    bytes
        .chunks_exact(2)
        .map(|chunk| {
            let sample = i16::from_le_bytes([chunk[0], chunk[1]]);
            sample as f32 / 32768.0
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pcm_i16le_to_f32_silence() {
        let bytes = vec![0u8; 100];
        let samples = pcm_i16le_to_f32(&bytes);
        assert_eq!(samples.len(), 50);
        for s in &samples {
            assert!(s.abs() < f32::EPSILON);
        }
    }

    #[test]
    fn test_pcm_i16le_to_f32_max_values() {
        // i16 max = 32767 → ~0.99997
        let max_bytes = 32767_i16.to_le_bytes();
        let samples = pcm_i16le_to_f32(&max_bytes);
        assert!((samples[0] - 0.99997).abs() < 0.001);

        // i16 min = -32768 → -1.0
        let min_bytes = (-32768_i16).to_le_bytes();
        let samples = pcm_i16le_to_f32(&min_bytes);
        assert!((samples[0] - (-1.0)).abs() < f32::EPSILON);
    }

    #[test]
    fn test_resample_passthrough_at_16khz() {
        let input: Vec<f32> = (0..160).map(|i| i as f32 / 160.0).collect();
        let output = resample_to_16khz(&input, 16000);
        assert_eq!(input.len(), output.len());
        assert_eq!(input, output);
    }

    #[test]
    fn test_resample_downsample_from_48khz() {
        // 48kHz → 16kHz = 3:1 ratio
        let input: Vec<f32> = (0..480).map(|i| (i as f32).sin()).collect();
        let output = resample_to_16khz(&input, 48000);
        assert_eq!(output.len(), 160);
    }

    #[test]
    fn test_whisper_state_new() {
        let state = WhisperState::new();
        assert!(!state.is_loaded());
        assert!(state.model_path().ends_with("ggml-small.en.bin"));
    }
}
