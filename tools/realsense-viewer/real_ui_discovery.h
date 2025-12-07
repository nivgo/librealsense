/*
Real UI Discovery Header
Extracts actual device/stream information from running RealSense viewer
*/

#ifndef REAL_UI_DISCOVERY_H
#define REAL_UI_DISCOVERY_H

#ifdef __cplusplus
extern "C" {
#endif

// Initialize the real UI discovery system
void init_real_ui_discovery();

// Cleanup the discovery system
void cleanup_real_ui_discovery();

// Generate JSON with real device/stream context
const char* generate_real_context_json();

// Export discovery results to file
void export_real_discovery_to_file(const char* filename);

#ifdef __cplusplus
}
#endif

#endif // REAL_UI_DISCOVERY_H
