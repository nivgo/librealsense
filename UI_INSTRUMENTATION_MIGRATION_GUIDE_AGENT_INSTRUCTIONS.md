# UI Instrumentation Migration Guide

## Purpose
This guide provides step-by-step instructions for migrating UI instrumentation to new versions of librealsense. The goal is to make all UI elements extractable for RL training by capturing every interactive component (buttons, sliders, dropdowns, etc.) into JSON output.

---

## Overview

The UI instrumentation system has **3 layers**:

1. **UI_ Macro Layer**: Replace ImGui calls with UI_ wrappers that log interactions
2. **RS_LOG_LAST Layer**: Add metadata logging for specific elements (camera options, device controls)
3. **Custom Function Layer**: Instrument custom UI functions (like CustomComboBox)

---

## Prerequisites

Before starting, ensure you have:
- Source version with UI instrumentation (reference branch)
- Target version to instrument (new/latest branch)
- Build environment set up (CMake 3.8+, C++17 compiler)

---

## Step 1: Copy Core Instrumentation Files

### 1.1 Copy ui_instrumentation.h
```bash
# Copy the instrumentation header
cp <source_branch>/common/ui_instrumentation.h <target_branch>/common/ui_instrumentation.h
```

**File**: `common/ui_instrumentation.h`

**Content**: Defines UI_ macros that wrap ImGui calls with logging

**Key macros**:
- `UI_Button`, `UI_Checkbox`, `UI_RadioButton`
- `UI_SliderFloat`, `UI_SliderInt`, `UI_InputText`
- `UI_Selectable`, `UI_TreeNode`, `UI_CollapsingHeader`
- `UI_BeginCombo`, `UI_EndCombo`, `UI_MenuItem`
- `UI_BeginPopup`, `UI_EndPopup`, `UI_BeginChild`

**Important**: Ensure variadic argument handling for macros like:
```cpp
#define UI_BeginChild(str_id, ...) (ImGui::BeginChild(str_id, ##__VA_ARGS__) ? (ui_dump_on_begin_child(str_id, ImGui::GetCurrentWindow()->ID, false), true) : false)
```

### 1.2 Verify RS_ Wrappers
Check that `tools/realsense-viewer/rs_imgui.h` has all RS_ wrapper functions:
- `RS_Button`, `RS_Checkbox`, `RS_Selectable`
- `RS_SliderFloat`, `RS_InputText`, etc.

These wrappers call the ui_dump functions and are used by UI_ macros.

---

## Step 2: Instrument Common Files (250+ Elements)

### 2.1 Identify Files to Instrument

Search for files with UI code:
```bash
cd common/
grep -l "ImGui::" *.cpp | grep -v "test"
```

**Priority files** (instrument these first):
1. `viewer.cpp` - Main 3D viewport (buttons, checkboxes, inputs)
2. `device-model.cpp` - Device panel controls
3. `subdevice-model.cpp` - Sensor/stream controls  
4. `option-model.cpp` - Camera option sliders/inputs ⚠️ **CRITICAL**
5. `calibration-model.cpp` - Calibration UI
6. `dds-model.cpp` - DDS configuration
7. `fw-update-helper.cpp` - Firmware updates
8. `on-chip-calib.cpp` - On-chip calibration
9. Other model/UI files

### 2.2 Add ui_instrumentation.h Include

**For each file**, add at the top (after other includes):
```cpp
#include "ui_instrumentation.h"
```

Example for `viewer.cpp`:
```cpp
#include "viewer.h"
#include "ui_instrumentation.h"  // ADD THIS
#include <imgui.h>
// ... other includes
```

### 2.3 Replace ImGui Calls with UI_ Macros

Use search and replace for each element type:

#### Buttons
```cpp
// Find:    ImGui::Button(
// Replace: UI_Button(

// Find:    ImGui::SmallButton(
// Replace: UI_SmallButton(
```

#### Checkboxes & Radio Buttons
```cpp
// Find:    ImGui::Checkbox(
// Replace: UI_Checkbox(

// Find:    ImGui::RadioButton(
// Replace: UI_RadioButton(
```

#### Selectables
```cpp
// Find:    ImGui::Selectable(
// Replace: UI_Selectable(
```

#### Tree Nodes & Headers
```cpp
// Find:    ImGui::TreeNode(
// Replace: UI_TreeNode(

// Find:    ImGui::TreeNodeEx(
// Replace: UI_TreeNodeEx(

// Find:    ImGui::CollapsingHeader(
// Replace: UI_CollapsingHeader(
```

#### Sliders
```cpp
// Find:    ImGui::SliderFloat(
// Replace: UI_SliderFloat(

// Find:    ImGui::SliderInt(
// Replace: UI_SliderInt(

// Find:    ImGui::DragFloat(
// Replace: UI_DragFloat(
```

#### Input Controls
```cpp
// Find:    ImGui::InputText(
// Replace: UI_InputText(

// Find:    ImGui::InputFloat(
// Replace: UI_InputFloat(

// Find:    ImGui::InputInt(
// Replace: UI_InputInt(
```

#### Menus & Popups
```cpp
// Find:    ImGui::BeginMenu(
// Replace: UI_BeginMenu(

// Find:    ImGui::MenuItem(
// Replace: UI_MenuItem(

// Find:    ImGui::BeginPopup(
// Replace: UI_BeginPopup(

// Find:    ImGui::BeginPopupModal(
// Replace: UI_BeginPopupModal(
```

#### Child Windows
```cpp
// Find:    ImGui::BeginChild(
// Replace: UI_BeginChild(

// Find:    ImGui::EndChild()
// Replace: UI_EndChild()
```

### 2.4 Handle Special Cases

**Combo boxes with inline arrays**: Sometimes ImGui::Combo needs special handling
```cpp
// If you see this pattern:
ImGui::Combo(label, &selected, "Option1\0Option2\0Option3\0\0");

// Leave it as ImGui::Combo - inline strings don't work with UI_ macros
// Or convert to array format:
const char* options[] = {"Option1", "Option2", "Option3"};
UI_Combo(label, &selected, options, 3);
```

**Conditional compilation**: Preserve existing #ifdef blocks
```cpp
#ifdef SOME_FEATURE
    UI_Button("Feature Button");
#endif
```

### 2.5 Verify Compilation

After each file:
```bash
cd build/
make -j4 2>&1 | tee /tmp/build.log
# Check for errors
tail -100 /tmp/build.log
```

**Common errors**:
- Missing includes: Add `#include "ui_instrumentation.h"`
- Macro argument mismatch: Check variadic args `##__VA_ARGS__`
- Overload resolution: Some ImGui functions have multiple signatures

---

## Step 3: Add RS_LOG_LAST Metadata (Critical for Options)

### 3.1 Instrument option-model.cpp ⚠️ **MOST IMPORTANT**

This file controls camera options (Exposure, Gain, White Balance, etc.)

**Add includes at top**:
```cpp
#include "ui_instrumentation.h"

#ifdef RS_DUMP_UI
#include "../tools/realsense-viewer/ui_dump.h"
#endif
```

### 3.2 Add RS_LOG_LAST for ROI Buttons

Find ROI button code (around line 115):
```cpp
if( ! dev->roi_checked )
{
    std::string caption = rsutils::string::from() << "Set ROI##" << button_label;
    // ADD THIS:
#ifdef RS_DUMP_UI
    std::string log_msg = rsutils::string::from() << "ROI_SET_BUTTON_ID:" << caption << "_LABEL:Set ROI_TYPE:button";
    RS_LOG_LAST("button", log_msg.c_str());
#endif
    if( UI_Button( caption.c_str(), { 55, 0 } ) )
    {
        dev->roi_checked = true;
    }
}
else
{
    std::string caption = rsutils::string::from() << "Cancel##" << button_label;
    // ADD THIS:
#ifdef RS_DUMP_UI
    std::string log_msg = rsutils::string::from() << "ROI_CANCEL_BUTTON_ID:" << caption << "_LABEL:Cancel ROI_TYPE:button";
    RS_LOG_LAST("button", log_msg.c_str());
#endif
    if( UI_Button( caption.c_str(), { 55, 0 } ) )
    {
        dev->roi_checked = false;
    }
}
```

### 3.3 Add RS_LOG_LAST for Combo Boxes

In `draw_combobox()` function (around line 292):
```cpp
if( RsImGui::CustomComboBox( id.c_str(), &selected, labels.data(), static_cast< int >( labels.size() ) ) )
{
    float tmp_value = range.min + range.step * selected;
    model.add_log( rsutils::string::from()
                   << "Setting " << opt << " to " << tmp_value << " (" << labels[selected] << ")" );
    set_option( opt, tmp_value, error_message );
    if( invalidate_flag )
        *invalidate_flag = true;
    item_clicked = true;
}
// ADD THIS:
#ifdef RS_DUMP_UI
RS_LOG_LAST("combo", endpoint->get_option_name(opt));
#endif
```

### 3.4 Add RS_LOG_LAST for Edit Mode Buttons

Find edit button code (around lines 418, 440):
```cpp
// For "Edit" button:
#ifdef RS_DUMP_UI
std::string log_msg = rsutils::string::from() << "OPTION_EDIT_BUTTON_ID:" << edit_id << "_LABEL:Edit Option_TYPE:button_OPTION:" << endpoint->get_option_name(opt);
RS_LOG_LAST("button", log_msg.c_str());
#endif
if( UI_Button( edit_id.c_str(), { 20, 20 } ) )

// For "Confirm Edit" button:
#ifdef RS_DUMP_UI
std::string log_msg = rsutils::string::from() << "OPTION_EDIT_CONFIRM_BUTTON_ID:" << edit_id << "_LABEL:Confirm Edit_TYPE:button_OPTION:" << endpoint->get_option_name(opt);
RS_LOG_LAST("button", log_msg.c_str());
#endif
if( UI_Button( edit_id.c_str(), { 20, 20 } ) )
```

### 3.5 Add RS_LOG_LAST for Sliders

In `draw_slider()` function, find slider code (around lines 577, 641):

**For integer sliders**:
```cpp
else
{
    slider_clicked = slider_unselected( opt, static_cast< float >( int_value ), error_message, model );
}
// ADD THIS:
#ifdef RS_DUMP_UI
RS_LOG_LAST("slider", endpoint->get_option_name(opt));
#endif
```

**For float sliders**:
```cpp
else
{
    slider_clicked = slider_unselected( opt, tmp_value, error_message, model );
}
// ADD THIS:
#ifdef RS_DUMP_UI
RS_LOG_LAST("slider", endpoint->get_option_name(opt));
#endif
```

### 3.6 Add RS_LOG_LAST for Checkboxes

In `draw_checkbox()` function (around line 675):
```cpp
set_option( opt, bool_value ? 1.f : 0.f, error_message );
if (invalidate_flag)
    *invalidate_flag = true;
}
// ADD THIS:
#ifdef RS_DUMP_UI
RS_LOG_LAST("checkbox", endpoint->get_option_name(opt));
#endif
if( ImGui::IsItemHovered() && description )
```

---

## Step 4: Instrument Custom UI Functions ⚠️ **CRITICAL FOR DROPDOWNS**

### 4.1 Instrument RsImGui::CustomComboBox

**File**: `third-party/imgui/realsense_imgui.cpp`

This is **THE MOST CRITICAL** custom function - it handles:
- Resolution dropdowns (640x480, 1280x720, etc.)
- Format dropdowns (Z16, RGB8, Y8, etc.)
- FPS dropdowns (30, 60, 90, etc.)
- Preset dropdowns

#### 4.1.1 Add RS_DUMP_UI Include

At top of file:
```cpp
/* License: Apache 2.0. See LICENSE file in root directory. */
/* Copyright(c) 2024 RealSense, Inc. All Rights Reserved. */

#include "realsense_imgui.h"
#include "imgui_impl_glfw.h"
#include "imgui_impl_opengl3.h"

// ADD THIS:
#ifdef RS_DUMP_UI
#include "../../tools/realsense-viewer/ui_dump.h"
#endif
```

#### 4.1.2 Add Complete Combo Instrumentation

Find `RsImGui::CustomComboBox` function and modify:

```cpp
bool RsImGui::CustomComboBox(const char* label, int* current_item, const char* const items[], int items_count)
{
    bool value_changed = false;
    
    // the preview value - selected item
    const char* preview_value = (*current_item >= 0 && *current_item < items_count) ? items[*current_item] : "Select an item";
    
    if (ImGui::BeginCombo(label, ""))
    {
        // ADD THIS - Log combo opening with current selection:
#ifdef RS_DUMP_UI
        ui_dump_combo_begin(label, preview_value);
#endif
        
        //insert combobox items
        for (int i = 0; i < items_count; i++)
        {
            const bool is_selected = (i == *current_item);
            if (ImGui::Selectable(items[i], is_selected))
            {
                *current_item = i;
                value_changed = true;
            }
            
            // ADD THIS - Log each combo option:
#ifdef RS_DUMP_UI
            ui_dump_combo_option(items[i], is_selected);
#endif
            
            if (is_selected)
                ImGui::SetItemDefaultFocus();
        }
        
        // ADD THIS - Log combo closing:
#ifdef RS_DUMP_UI
        ui_dump_combo_end();
#endif
        
        ImGui::EndCombo();
    } else {
        // ADD THIS - Log closed combo state:
#ifdef RS_DUMP_UI
        RS_LOG_LAST("combo", label);
#endif
    }
    
    // ... rest of function (text centering, etc.)
}
```

**Why these 4 calls are needed**:
1. `ui_dump_combo_begin()` - Captures combo opening + current selection
2. `ui_dump_combo_option()` - Lists ALL available options (critical for RL agent to see action space)
3. `ui_dump_combo_end()` - Marks end of options
4. `RS_LOG_LAST()` - Logs closed combo state

### 4.2 Check for Other Custom Functions

Search for other custom UI functions:
```bash
grep -rn "bool.*Combo\|bool.*Slider\|bool.*Button" third-party/imgui/*.cpp
```

If found, apply similar instrumentation pattern.

---

## Step 5: Build and Test

### 5.1 Full Rebuild
```bash
cd build/
rm -rf *  # Clean build
cmake ..
make -j4 2>&1 | tee /tmp/full_build.log
```

### 5.2 Check Build Success
```bash
# Should show 100% completion
tail -50 /tmp/full_build.log

# Verify executable exists
ls -lh Release/realsense-viewer
file Release/realsense-viewer
```

### 5.3 Test with Device

```bash
# Run viewer
cd Release/
./realsense-viewer

# Connect RealSense device
# Interact with UI:
# - Click buttons
# - Adjust sliders
# - Change dropdowns (resolution, format, FPS)
# - Open menus
```

### 5.4 Verify JSON Output

```bash
# Check JSON files are being created
ls -l /tmp/rs-viewer-ui/

# View latest JSON
cat /tmp/rs-viewer-ui/frame_0001.json | jq .

# Count UI elements
cat /tmp/rs-viewer-ui/frame_0001.json | jq '.ui_elements | length'
# Should be 40+ with device open

# Check for dropdowns
cat /tmp/rs-viewer-ui/frame_*.json | jq '.ui_elements[] | select(.type == "combo")'

# Check for specific elements
cat /tmp/rs-viewer-ui/frame_*.json | jq '.ui_elements[] | select(.label | contains("resolution"))'
cat /tmp/rs-viewer-ui/frame_*.json | jq '.ui_elements[] | select(.label | contains("Exposure"))'
```

### 5.5 Expected JSON Structure

**Closed combo box**:
```json
{
  "type": "combo",
  "label": "##device_sensor_resolution",
  "value": "640x480",
  "position": [x, y],
  "window": "Device Panel"
}
```

**Open combo box**:
```json
{
  "type": "combo",
  "label": "##device_sensor_resolution",
  "state": "open",
  "preview": "640x480",
  "options": [
    {"label": "320x240", "selected": false},
    {"label": "640x480", "selected": true},
    {"label": "1280x720", "selected": false}
  ]
}
```

**Camera option slider**:
```json
{
  "type": "slider",
  "label": "Exposure",
  "value": 166.0,
  "min": 1.0,
  "max": 10000.0,
  "metadata": "Exposure"
}
```

---

## Step 6: Troubleshooting

### 6.1 Missing Elements in JSON

**Problem**: UI elements don't appear in JSON output

**Solutions**:
1. Check file includes `ui_instrumentation.h`
2. Verify ImGui:: was replaced with UI_
3. Check build uses `-DRS_DUMP_UI` flag
4. Ensure RS_ wrappers exist in rs_imgui.h

### 6.2 Compilation Errors

**Error**: `UI_Button` undefined
**Solution**: Add `#include "ui_instrumentation.h"`

**Error**: Macro argument mismatch
**Solution**: Check variadic args `##__VA_ARGS__`

**Error**: `ui_dump_combo_begin` undefined
**Solution**: Add `#ifdef RS_DUMP_UI` include in realsense_imgui.cpp

### 6.3 Dropdown Options Missing

**Problem**: Resolution/Format/FPS dropdowns show empty

**Solution**: Verify CustomComboBox has all 4 instrumentation points:
- `ui_dump_combo_begin()`
- `ui_dump_combo_option()` (in loop)
- `ui_dump_combo_end()`
- `RS_LOG_LAST()` (when closed)

### 6.4 Option Metadata Missing

**Problem**: Sliders/checkboxes don't show option names

**Solution**: Add RS_LOG_LAST calls in option-model.cpp as shown in Step 3

---

## Step 7: Verification Checklist

Use this checklist to ensure complete instrumentation:

### Core Files
- [ ] `ui_instrumentation.h` copied and includes all macros
- [ ] `rs_imgui.h` has RS_ wrapper functions
- [ ] `ui_dump.h` has dump functions (ui_dump_combo_begin, etc.)

### Common Files (17 files minimum)
- [ ] `viewer.cpp` - UI_ macros added
- [ ] `device-model.cpp` - UI_ macros added
- [ ] `subdevice-model.cpp` - UI_ macros added
- [ ] `option-model.cpp` - UI_ macros + RS_LOG_LAST (8 calls)
- [ ] `calibration-model.cpp` - UI_ macros added
- [ ] `dds-model.cpp` - UI_ macros added
- [ ] `fw-update-helper.cpp` - UI_ macros added
- [ ] `graph-model.cpp` - UI_ macros added
- [ ] `hdr-model.cpp` - UI_ macros added
- [ ] `measurement.cpp` - UI_ macros added
- [ ] `model-views.cpp` - UI_ macros added
- [ ] `notifications.cpp` - UI_ macros added
- [ ] `on-chip-calib.cpp` - UI_ macros added
- [ ] `output-model.cpp` - UI_ macros added
- [ ] `stream-model.cpp` - UI_ macros added
- [ ] `updates-model.cpp` - UI_ macros added
- [ ] `ux-window.cpp` - UI_ macros added

### Custom Functions
- [ ] `CustomComboBox` in realsense_imgui.cpp - Complete instrumentation

### Build
- [ ] Clean build successful (100%)
- [ ] realsense-viewer executable created
- [ ] No compilation errors or warnings

### Runtime Testing
- [ ] JSON files created in /tmp/rs-viewer-ui/
- [ ] Buttons appear in JSON
- [ ] Sliders appear in JSON with metadata
- [ ] Checkboxes appear in JSON
- [ ] Dropdown menus captured
- [ ] Dropdown OPTIONS enumerated (resolution, format, FPS)
- [ ] Camera option names captured (Exposure, Gain, etc.)
- [ ] Window hierarchy preserved
- [ ] 40+ UI elements when device panel open

---

## Quick Reference: File Changes Summary

### Files Modified
1. **common/ui_instrumentation.h** - Core macro definitions
2. **common/viewer.cpp** - 68 UI_ replacements
3. **common/device-model.cpp** - 50+ UI_ replacements
4. **common/option-model.cpp** - UI_ replacements + 8 RS_LOG_LAST calls
5. **common/subdevice-model.cpp** - UI_ replacements
6. **common/calibration-model.cpp** - UI_ replacements
7. **common/dds-model.cpp** - UI_ replacements
8. **common/fw-update-helper.cpp** - UI_ replacements
9. **common/graph-model.cpp** - UI_ replacements
10. **common/hdr-model.cpp** - UI_ replacements
11. **common/measurement.cpp** - UI_ replacements
12. **common/model-views.cpp** - UI_ replacements
13. **common/notifications.cpp** - UI_ replacements
14. **common/on-chip-calib.cpp** - UI_ replacements
15. **common/output-model.cpp** - UI_ replacements
16. **common/stream-model.cpp** - UI_ replacements
17. **common/updates-model.cpp** - UI_ replacements
18. **common/ux-window.cpp** - UI_ replacements
19. **common/ux-alignment.cpp** - UI_ replacements
20. **third-party/imgui/realsense_imgui.cpp** - CustomComboBox instrumentation

### Typical Changes Per File
- Add: `#include "ui_instrumentation.h"`
- Replace: ~20-70 ImGui:: calls with UI_ macros
- Verify: Compilation succeeds

### Critical Files (Don't Skip!)
⚠️ **option-model.cpp** - Camera options (Exposure, Gain, etc.)
⚠️ **realsense_imgui.cpp** - CustomComboBox (Resolution, Format, FPS dropdowns)

---

## Tips for Efficiency

### 1. Use Automated Search/Replace
```bash
# Example: Replace all buttons in a file
sed -i 's/ImGui::Button(/UI_Button(/g' viewer.cpp
```

### 2. Process Files in Batches
- Batch 1: viewer.cpp, device-model.cpp (main UI)
- Batch 2: option-model.cpp (critical for options)
- Batch 3: All other model files
- Batch 4: Custom functions (realsense_imgui.cpp)

### 3. Incremental Building
Build after each file to catch errors early:
```bash
make viewer.cpp.o
```

### 4. Diff Against Source
```bash
# Compare instrumented vs non-instrumented
diff -u original/viewer.cpp instrumented/viewer.cpp
```

---

## Version-Specific Notes

### Breaking Changes to Watch For

When migrating to a new librealsense version:

1. **New UI Elements**: Check for new buttons/sliders/dropdowns
2. **API Changes**: ImGui signatures may change
3. **New Files**: Look for new model/UI files to instrument
4. **Removed Files**: Update file list
5. **Renamed Functions**: Update macro replacements

### Compatibility Check
```bash
# Find all ImGui calls that might need instrumentation
grep -rn "ImGui::" common/*.cpp | grep -v "ImGui::Text\|ImGui::SameLine\|ImGui::SetCursor"
```

---

## Success Criteria

Your instrumentation is complete when:

✅ Build succeeds at 100%
✅ JSON files created when viewer runs
✅ 40+ UI elements captured with device open
✅ All dropdowns show their options
✅ Camera options (Exposure, Gain) have metadata
✅ Buttons, sliders, checkboxes all appear
✅ Window hierarchy preserved
✅ No runtime crashes

---

## Support & Debugging

### Enable Debug Logging
```cpp
// In ui_dump.cpp, add debug prints:
#define UI_DEBUG 1

#ifdef UI_DEBUG
#define DEBUG_LOG(msg) std::cout << "UI_DUMP: " << msg << std::endl
#else
#define DEBUG_LOG(msg)
#endif
```

### Check JSON Schema
```bash
# Validate JSON structure
cat /tmp/rs-viewer-ui/frame_0001.json | jq 'type'
cat /tmp/rs-viewer-ui/frame_0001.json | jq '.ui_elements[0]'
```

### Compare Output
```bash
# Compare JSON from source vs target version
diff <(cat source_output.json | jq -S .) <(cat target_output.json | jq -S .)
```

---

## Appendix: Common Patterns

### Pattern 1: Simple Button
```cpp
// Before:
if (ImGui::Button("Click Me")) {
    do_action();
}

// After:
if (UI_Button("Click Me")) {
    do_action();
}
```

### Pattern 2: Slider with Metadata
```cpp
// Before:
ImGui::SliderFloat("Exposure", &value, 0, 100);

// After:
UI_SliderFloat("Exposure", &value, 0, 100);
// Plus in option-model.cpp:
#ifdef RS_DUMP_UI
RS_LOG_LAST("slider", "Exposure");
#endif
```

### Pattern 3: Dropdown with Options
```cpp
// In CustomComboBox function:
#ifdef RS_DUMP_UI
ui_dump_combo_begin(label, preview_value);
#endif
for (int i = 0; i < items_count; i++) {
    if (ImGui::Selectable(items[i], is_selected)) {
        *current_item = i;
    }
#ifdef RS_DUMP_UI
    ui_dump_combo_option(items[i], is_selected);
#endif
}
#ifdef RS_DUMP_UI
ui_dump_combo_end();
#endif
```

---

## Final Notes

- **Test thoroughly** before considering migration complete
- **Document** any version-specific changes
- **Keep** this guide updated as the instrumentation system evolves
- **Share** improvements back to the team

**Estimated Time**: 4-6 hours for full migration (experienced developer)

**Priority**: HIGH - UI instrumentation is critical for RL training data collection

---

## Contact & Resources

- UI Dump System Documentation: `tools/realsense-viewer/ui_dump.h`
- RS Wrapper Documentation: `tools/realsense-viewer/rs_imgui.h`
- ImGui Documentation: https://github.com/ocornut/imgui

---

**Document Version**: 1.0
**Last Updated**: December 2025
**Status**: Production Ready ✅
