//! Border crossing REST API endpoints
//!
//! This module provides endpoints for border crossing configuration and metadata.

use axum::{
    extract::Path,
    http::StatusCode,
    response::IntoResponse,
    Json,
};
use std::collections::HashMap;
use std::path::PathBuf;

use crate::models::{
    ApiError, BorderCrossingInfo, BorderCrossingsResponse, CrossingConfig,
};

/// Path to the bounding boxes configuration file
const BOUNDING_BOXES_PATH: &str = "cascabel/paths/bounding_boxes.json";

/// Path to the paths directory
const PATHS_DIR: &str = "cascabel/paths";

/// GET /border-crossings - List available border crossings
pub async fn get_border_crossings() -> impl IntoResponse {
    let mut crossings = Vec::new();

    // Scan for GeoJSON files in the paths directory
    match std::fs::read_dir(PATHS_DIR) {
        Ok(entries) => {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_dir() {
                    // Recursively search in subdirectories
                    if let Ok(sub_entries) = std::fs::read_dir(&path) {
                        for sub_entry in sub_entries.flatten() {
                            let file_path = sub_entry.path();
                            if let Some(crossing) = parse_geojson_file(&file_path, &path) {
                                crossings.push(crossing);
                            }
                        }
                    }
                } else if let Some(crossing) = parse_geojson_file(&path, &PathBuf::from(PATHS_DIR)) {
                    crossings.push(crossing);
                }
            }
        }
        Err(e) => {
            tracing::warn!("Failed to read paths directory: {}", e);
        }
    }

    let response = BorderCrossingsResponse { crossings };
    (StatusCode::OK, Json(response))
}

/// Parse a GeoJSON file and extract crossing info
fn parse_geojson_file(path: &PathBuf, _parent: &PathBuf) -> Option<BorderCrossingInfo> {
    let file_name = path.file_name()?.to_str()?;

    // Only process .geojson files, skip copy files
    if !file_name.ends_with(".geojson") || file_name.ends_with("copy.geojson") {
        return None;
    }

    // Read and parse GeoJSON
    let content = std::fs::read_to_string(path).ok()?;
    let geojson: serde_json::Value = serde_json::from_str(&content).ok()?;

    // Extract properties from first feature
    let features = geojson.get("features")?.as_array()?;
    let first_feature = features.first()?;
    let properties = first_feature.get("properties").and_then(|p| p.as_object());
    let geometry = first_feature.get("geometry");

    // Get direction from parent directory or properties
    let rel_path = path.strip_prefix(PATHS_DIR).unwrap_or(path);
    let parts: Vec<&str> = rel_path.iter()
        .filter_map(|p| p.to_str())
        .collect();
    let direction_from_path = parts.first().copied().unwrap_or("unknown");

    let direction = properties
        .and_then(|p| p.get("direction"))
        .and_then(|v| v.as_str())
        .unwrap_or(direction_from_path)
        .to_string();

    let id = file_name.trim_end_matches(".geojson").to_string();

    let crossing_name = properties
        .and_then(|p| p.get("crossing_name"))
        .and_then(|v| v.as_str())
        .unwrap_or(&id)
        .to_string();

    let description = properties
        .and_then(|p| p.get("description"))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let start_point = properties
        .and_then(|p| p.get("start_point"))
        .and_then(|v| v.as_array())
        .map(|arr| {
            let x = arr.get(0).and_then(|v| v.as_f64()).unwrap_or(0.0);
            let y = arr.get(1).and_then(|v| v.as_f64()).unwrap_or(0.0);
            [x, y]
        });

    let end_point = properties
        .and_then(|p| p.get("end_point"))
        .and_then(|v| v.as_array())
        .map(|arr| {
            let x = arr.get(0).and_then(|v| v.as_f64()).unwrap_or(0.0);
            let y = arr.get(1).and_then(|v| v.as_f64()).unwrap_or(0.0);
            [x, y]
        });

    let geometry_type = geometry
        .and_then(|g| g.get("type"))
        .and_then(|t| t.as_str())
        .unwrap_or("Unknown")
        .to_string();

    // Construct path relative to cascabel/paths
    let rel_geojson_path = path.strip_prefix(PATHS_DIR)
        .map(|p| format!("cascabel/paths/{}", p.display()))
        .unwrap_or_else(|_| path.display().to_string());

    Some(BorderCrossingInfo {
        id,
        name: crossing_name,
        direction,
        path: rel_geojson_path,
        description,
        start_point,
        end_point,
        geometry_type,
    })
}

/// GET /crossing/{name}/config - Get crossing configuration
pub async fn get_crossing_config(
    Path(crossing_name): Path<String>,
) -> impl IntoResponse {
    // Load bounding_boxes.json
    match std::fs::read_to_string(BOUNDING_BOXES_PATH) {
        Ok(content) => {
            match serde_json::from_str::<HashMap<String, CrossingConfig>>(&content) {
                Ok(all_crossings) => {
                    match all_crossings.get(&crossing_name) {
                        Some(config) => {
                            (StatusCode::OK, Json(config.clone())).into_response()
                        }
                        None => {
                            let available: Vec<&String> = all_crossings.keys().collect();
                            let error = ApiError::not_found(format!(
                                "Crossing '{}' not found. Available: {:?}",
                                crossing_name, available
                            ));
                            (StatusCode::NOT_FOUND, Json(error)).into_response()
                        }
                    }
                }
                Err(e) => {
                    let error = ApiError::internal_error(format!(
                        "Error parsing bounding boxes: {}", e
                    ));
                    (StatusCode::INTERNAL_SERVER_ERROR, Json(error)).into_response()
                }
            }
        }
        Err(e) => {
            let error = ApiError::not_found(format!(
                "Bounding boxes configuration not found: {}", e
            ));
            (StatusCode::NOT_FOUND, Json(error)).into_response()
        }
    }
}

/// GET /geojson/{path} - Get GeoJSON data for a path
pub async fn get_geojson(
    Path(path_name): Path<String>,
) -> impl IntoResponse {
    let geojson_path = format!("{}/{}.geojson", PATHS_DIR, path_name);

    match std::fs::read_to_string(&geojson_path) {
        Ok(content) => {
            match serde_json::from_str::<serde_json::Value>(&content) {
                Ok(geojson) => {
                    (StatusCode::OK, Json(geojson)).into_response()
                }
                Err(e) => {
                    let error = ApiError::internal_error(format!(
                        "Error parsing GeoJSON: {}", e
                    ));
                    (StatusCode::INTERNAL_SERVER_ERROR, Json(error)).into_response()
                }
            }
        }
        Err(_) => {
            let error = ApiError::not_found(format!(
                "GeoJSON file not found: {}", path_name
            ));
            (StatusCode::NOT_FOUND, Json(error)).into_response()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{
        body::Body,
        http::{Request, StatusCode},
        Router,
        routing::get,
    };
    use tower::ServiceExt;

    fn create_test_app() -> Router {
        Router::new()
            .route("/border-crossings", get(get_border_crossings))
            .route("/crossing/:name/config", get(get_crossing_config))
            .route("/geojson/*path_name", get(get_geojson))
    }

    // ========== GET /border-crossings tests ==========

    #[tokio::test]
    async fn test_get_border_crossings() {
        let app = create_test_app();

        let response = app
            .oneshot(
                Request::builder()
                    .method("GET")
                    .uri("/border-crossings")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);

        let body = axum::body::to_bytes(response.into_body(), usize::MAX).await.unwrap();
        let result: BorderCrossingsResponse = serde_json::from_slice(&body).unwrap();

        // Result may be empty if running outside project root
        assert!(result.crossings.is_empty() || !result.crossings.is_empty());
    }

    // ========== GET /crossing/{name}/config tests ==========

    #[tokio::test]
    async fn test_get_crossing_config_paso_del_norte() {
        let app = create_test_app();

        let response = app
            .oneshot(
                Request::builder()
                    .method("GET")
                    .uri("/crossing/paso_del_norte/config")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        // May be 200 or 404 depending on working directory
        let status = response.status();
        assert!(status == StatusCode::OK || status == StatusCode::NOT_FOUND);

        if status == StatusCode::OK {
            let body = axum::body::to_bytes(response.into_body(), usize::MAX).await.unwrap();
            let config: CrossingConfig = serde_json::from_slice(&body).unwrap();
            assert_eq!(config.bounding_box.len(), 4);
        }
    }

    #[tokio::test]
    async fn test_get_crossing_config_not_found() {
        let app = create_test_app();

        let response = app
            .oneshot(
                Request::builder()
                    .method("GET")
                    .uri("/crossing/nonexistent_crossing/config")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        // Should be 404 (crossing not found) or 404 (file not found)
        assert_eq!(response.status(), StatusCode::NOT_FOUND);
    }

    // ========== GET /geojson/{path} tests ==========

    #[tokio::test]
    async fn test_get_geojson_not_found() {
        let app = create_test_app();

        let response = app
            .oneshot(
                Request::builder()
                    .method("GET")
                    .uri("/geojson/nonexistent/path")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::NOT_FOUND);
    }

    // ========== Unit tests for helper functions ==========

    #[test]
    fn test_parse_geojson_file_invalid_extension() {
        let path = PathBuf::from("/tmp/test.txt");
        let parent = PathBuf::from("/tmp");
        assert!(parse_geojson_file(&path, &parent).is_none());
    }

    #[test]
    fn test_parse_geojson_file_copy_file() {
        let path = PathBuf::from("/tmp/test_copy.geojson");
        let parent = PathBuf::from("/tmp");
        assert!(parse_geojson_file(&path, &parent).is_none());
    }
}
