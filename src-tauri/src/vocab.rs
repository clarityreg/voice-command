use std::path::PathBuf;

fn vocab_file_path() -> PathBuf {
    dirs::home_dir()
        .unwrap_or_default()
        .join(".clarity")
        .join("whisper-vocab.txt")
}

#[tauri::command]
pub async fn get_custom_vocab() -> Result<Vec<String>, String> {
    let path = vocab_file_path();
    if !path.exists() {
        return Ok(Vec::new());
    }
    let content = tokio::fs::read_to_string(&path)
        .await
        .map_err(|e| format!("Failed to read vocab file: {e}"))?;
    Ok(content
        .lines()
        .map(|l| l.trim().to_string())
        .filter(|l| !l.is_empty())
        .collect())
}

#[tauri::command]
pub async fn save_custom_vocab(terms: Vec<String>) -> Result<(), String> {
    let path = vocab_file_path();
    if let Some(parent) = path.parent() {
        tokio::fs::create_dir_all(parent)
            .await
            .map_err(|e| format!("Failed to create directory: {e}"))?;
    }
    let content = terms.join("\n");
    tokio::fs::write(&path, content)
        .await
        .map_err(|e| format!("Failed to write vocab file: {e}"))?;
    Ok(())
}

/// Compose an initial prompt from custom vocabulary terms.
/// This biases whisper's decoder toward recognizing these terms.
pub fn compose_initial_prompt(terms: &[String]) -> String {
    if terms.is_empty() {
        return String::new();
    }
    format!(
        "The following terms may appear: {}.",
        terms.join(", ")
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_compose_initial_prompt_empty() {
        assert_eq!(compose_initial_prompt(&[]), "");
    }

    #[test]
    fn test_compose_initial_prompt_single_term() {
        let terms = vec!["PostHog".to_string()];
        assert_eq!(
            compose_initial_prompt(&terms),
            "The following terms may appear: PostHog."
        );
    }

    #[test]
    fn test_compose_initial_prompt_multiple_terms() {
        let terms = vec![
            "PostHog".to_string(),
            "OWASP".to_string(),
            "CVE".to_string(),
        ];
        assert_eq!(
            compose_initial_prompt(&terms),
            "The following terms may appear: PostHog, OWASP, CVE."
        );
    }
}
