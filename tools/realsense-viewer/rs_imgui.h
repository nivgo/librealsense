#pragma once

#include <imgui.h>
#include "ui_dump.h"
#include <cstdarg>

// Thin wrappers for ImGui widgets to automatically log them for UI dump
// This helps to avoid sprinkling RS_LOG_LAST everywhere and makes the code cleaner.

inline bool RS_Button(const char* label, const ImVec2& size = ImVec2(0, 0))
{
    bool result = ImGui::Button(label, size);
    RS_LOG_LAST("button", label);
    return result;
}

inline bool RS_SmallButton(const char* label)
{
    bool result = ImGui::SmallButton(label);
    RS_LOG_LAST("button", label);
    return result;
}

inline bool RS_ArrowButton(const char* str_id, ImGuiDir dir)
{
    bool result = ImGui::ArrowButton(str_id, dir);
    RS_LOG_LAST("button", str_id);
    return result;
}

inline bool RS_Checkbox(const char* label, bool* v)
{
    bool result = ImGui::Checkbox(label, v);
    ui_dump_on_item_with_state("checkbox", label, *v);
    return result;
}

inline bool RS_RadioButton(const char* label, bool active)
{
    bool result = ImGui::RadioButton(label, active);
    RS_LOG_LAST("radiobutton", label);
    return result;
}

inline bool RS_Selectable(const char* label, bool selected = false, ImGuiSelectableFlags flags = 0, const ImVec2& size = ImVec2(0, 0))
{
    bool result = ImGui::Selectable(label, selected, flags, size);
    ui_dump_on_item_with_state("selectable", label, false, 0.0f, selected ? 1 : 0);
    return result;
}

inline bool RS_SliderFloat(const char* label, float* v, float v_min, float v_max, const char* format = "%.3f", float power = 1.0f)
{
    bool result = ImGui::SliderFloat(label, v, v_min, v_max, format, power);
    ui_dump_on_item_with_state("slider", label, false, *v);
    return result;
}

inline bool RS_SliderInt(const char* label, int* v, int v_min, int v_max, const char* format = "%d")
{
    bool result = ImGui::SliderInt(label, v, v_min, v_max, format);
    ui_dump_on_item_with_state("slider", label, false, (float)*v);
    return result;
}

inline bool RS_BeginCombo(const char* label, const char* preview_value, ImGuiComboFlags flags = 0)
{
    bool result = ImGui::BeginCombo(label, preview_value, flags);
    if (result) {
        ui_dump_combo_begin(label, preview_value);
    } else {
        // Log the combo even when closed - this ensures dropdowns are always visible
        ui_dump_combo_closed(label, preview_value);
    }
    return result;
}

inline void RS_EndCombo()
{
    ui_dump_combo_end();
    ImGui::EndCombo();
}

inline bool RS_BeginMenu(const char* label, bool enabled = true)
{
    bool result = ImGui::BeginMenu(label, enabled);
    if (result) {
        ui_dump_on_begin_popup(label);
    }
    return result;
}

inline void RS_EndMenu()
{
    ui_dump_on_end_popup();
    ImGui::EndMenu();
}

inline bool RS_MenuItem(const char* label, const char* shortcut = NULL, bool selected = false, bool enabled = true)
{
    bool result = ImGui::MenuItem(label, shortcut, selected, enabled);
    RS_LOG_LAST("menuitem", label);
    return result;
}

inline bool RS_CollapsingHeader(const char* label, ImGuiTreeNodeFlags flags = 0)
{
    bool is_open = ImGui::CollapsingHeader(label, flags);
    ui_dump_on_header(label, is_open);
    return is_open;
}

inline bool RS_TreeNode(const char* label)
{
    bool is_open = ImGui::TreeNode(label);
    ui_dump_on_header(label, is_open);
    if (is_open) {
        ui_dump_on_header_end_on_pop();
    }
    return is_open;
}

inline bool RS_TreeNodeEx(const char* label, ImGuiTreeNodeFlags flags)
{
    bool is_open = ImGui::TreeNodeEx(label, flags);
    ui_dump_on_header(label, is_open);
    if (is_open) {
        ui_dump_on_header_end_on_pop();
    }
    return is_open;
}

inline void RS_TreePop()
{
    ui_dump_on_header_end();
    ImGui::TreePop();
}

inline bool RS_BeginTabItem(const char* label, bool* p_open = NULL, ImGuiTabItemFlags flags = 0)
{
    bool is_selected = ImGui::BeginTabItem(label, p_open, flags);
    ui_dump_on_tabitem(label, is_selected);
    return is_selected;
}

inline void RS_EndTabItem()
{
    ImGui::EndTabItem();
}

inline bool RS_Begin(const char* name, bool* p_open = NULL, ImGuiWindowFlags flags = 0)
{
    bool scrollable = !(flags & ImGuiWindowFlags_NoScrollbar);
    bool result = ImGui::Begin(name, p_open, flags);
    if (result) {
        ui_dump_on_begin_window(name, ImGui::GetCurrentWindow()->ID, scrollable);
    }
    return result;
}

inline void RS_End()
{
    ui_dump_on_end_window();
    ImGui::End();
}

inline bool RS_BeginChild(const char* str_id, const ImVec2& size = ImVec2(0, 0), bool border = false, ImGuiWindowFlags flags = 0)
{
    bool scrollable = !(flags & ImGuiWindowFlags_NoScrollbar);
    bool result = ImGui::BeginChild(str_id, size, border, flags);
    if (result) {
        ui_dump_on_begin_child(str_id, ImGui::GetCurrentWindow()->ID, scrollable);
    }
    return result;
}

inline void RS_EndChild()
{
    ui_dump_on_end_child();
    ImGui::EndChild();
}

inline bool RS_BeginPopup(const char* str_id, ImGuiWindowFlags flags = 0)
{
    bool result = ImGui::BeginPopup(str_id, flags);
    if (result) {
        ui_dump_on_begin_popup(str_id);
    }
    return result;
}

inline bool RS_BeginPopupModal(const char* name, bool* p_open = NULL, ImGuiWindowFlags flags = 0)
{
    bool result = ImGui::BeginPopupModal(name, p_open, flags);
    if (result) {
        ui_dump_on_begin_popup(name);
    }
    return result;
}

inline bool RS_BeginPopupContextItem(const char* str_id = NULL, ImGuiPopupFlags popup_flags = 1)
{
    bool result = ImGui::BeginPopupContextItem(str_id, popup_flags);
    if (result) {
        ui_dump_on_begin_popup(str_id);
    }
    return result;
}

inline void RS_EndPopup()
{
    ui_dump_on_end_popup();
    ImGui::EndPopup();
}

// Additional wrapper functions for comprehensive coverage

inline bool RS_ImageButton(ImTextureID texture, const ImVec2& size, const ImVec2& uv0 = ImVec2(0, 0), const ImVec2& uv1 = ImVec2(1, 1), int frame_padding = -1, const ImVec4& bg_col = ImVec4(0, 0, 0, 0), const ImVec4& tint_col = ImVec4(1, 1, 1, 1))
{
    bool result = ImGui::ImageButton(texture, size, uv0, uv1, frame_padding, bg_col, tint_col);
    RS_LOG_LAST("imagebutton", "");
    return result;
}

inline bool RS_DragFloat(const char* label, float* v, float v_speed = 1.0f, float v_min = 0.0f, float v_max = 0.0f, const char* format = "%.3f", float power = 1.0f)
{
    bool result = ImGui::DragFloat(label, v, v_speed, v_min, v_max, format, power);
    RS_LOG_LAST("drag", label);
    return result;
}

inline bool RS_DragInt(const char* label, int* v, float v_speed = 1.0f, int v_min = 0, int v_max = 0, const char* format = "%d")
{
    bool result = ImGui::DragInt(label, v, v_speed, v_min, v_max, format);
    RS_LOG_LAST("drag", label);
    return result;
}

inline bool RS_InputText(const char* label, char* buf, size_t buf_size, ImGuiInputTextFlags flags = 0, ImGuiInputTextCallback callback = NULL, void* user_data = NULL)
{
    bool result = ImGui::InputText(label, buf, buf_size, flags, callback, user_data);
    ui_dump_input_text(label, buf);
    return result;
}

inline bool RS_InputInt(const char* label, int* v, int step = 1, int step_fast = 100, ImGuiInputTextFlags flags = 0)
{
    bool result = ImGui::InputInt(label, v, step, step_fast, flags);
    RS_LOG_LAST("input_int", label);
    return result;
}

inline bool RS_InputFloat(const char* label, float* v, float step = 0.0f, float step_fast = 0.0f, const char* format = "%.3f", ImGuiInputTextFlags flags = 0)
{
    bool result = ImGui::InputFloat(label, v, step, step_fast, format, flags);
    RS_LOG_LAST("input_float", label);
    return result;
}

inline bool RS_ColorEdit3(const char* label, float col[3], ImGuiColorEditFlags flags = 0)
{
    bool result = ImGui::ColorEdit3(label, col, flags);
    RS_LOG_LAST("color_edit", label);
    return result;
}

inline bool RS_ColorEdit4(const char* label, float col[4], ImGuiColorEditFlags flags = 0)
{
    bool result = ImGui::ColorEdit4(label, col, flags);
    RS_LOG_LAST("color_edit", label);
    return result;
}

inline bool RS_ColorPicker3(const char* label, float col[3], ImGuiColorEditFlags flags = 0)
{
    bool result = ImGui::ColorPicker3(label, col, flags);
    RS_LOG_LAST("color_picker", label);
    return result;
}

inline bool RS_ColorPicker4(const char* label, float col[4], ImGuiColorEditFlags flags = 0, const float* ref_col = NULL)
{
    bool result = ImGui::ColorPicker4(label, col, flags, ref_col);
    RS_LOG_LAST("color_picker", label);
    return result;
}

inline bool RS_ListBox(const char* label, int* current_item, const char* const items[], int items_count, int height_in_items = -1)
{
    bool result = ImGui::ListBox(label, current_item, items, items_count, height_in_items);
    RS_LOG_LAST("listbox", label);
    return result;
}

inline void RS_ProgressBar(float fraction, const ImVec2& size_arg = ImVec2(-1, 0), const char* overlay = NULL)
{
    ImGui::ProgressBar(fraction, size_arg, overlay);
    ui_dump_progress_bar(overlay ? overlay : "progress", fraction);
}

inline bool RS_BeginMainMenuBar()
{
    bool result = ImGui::BeginMainMenuBar();
    if (result) {
        ui_dump_menubar_begin("MainMenuBar");
    }
    return result;
}

inline void RS_EndMainMenuBar()
{
    ui_dump_menubar_end();
    ImGui::EndMainMenuBar();
}

inline bool RS_BeginMenuBar()
{
    bool result = ImGui::BeginMenuBar();
    if (result) {
        ui_dump_menubar_begin("MenuBar");
    }
    return result;
}

inline void RS_EndMenuBar()
{
    ui_dump_menubar_end();
    ImGui::EndMenuBar();
}

inline bool RS_BeginTable(const char* str_id, int column, ImGuiTableFlags flags = 0, const ImVec2& outer_size = ImVec2(0.0f, 0.0f), float inner_width = 0.0f)
{
    bool result = ImGui::BeginTable(str_id, column, flags, outer_size, inner_width);
    if (result) {
        ui_dump_table_begin(str_id, column);
    }
    return result;
}

inline void RS_EndTable()
{
    ui_dump_table_end();
    ImGui::EndTable();
}

inline void RS_TableNextRow(ImGuiTableRowFlags row_flags = 0, float min_row_height = 0.0f)
{
    ImGui::TableNextRow(row_flags, min_row_height);
    ui_dump_table_row_begin();
}

inline void RS_TableSetupColumn(const char* label, ImGuiTableColumnFlags flags = 0, float init_width_or_weight = 0.0f, ImGuiID user_id = 0)
{
    ImGui::TableSetupColumn(label, flags, init_width_or_weight, user_id);
    ui_dump_table_header(label);
}

inline void RS_TableNextColumn()
{
    ImGui::TableNextColumn();
    // Simple table cell tracking without complex ID generation
    if (g_uidump.enabled) {
        ui_dump_table_cell("", false); // Empty content, not editable by default
    }
}

// Enhanced table cell with content tracking
inline void RS_TableCellText(const char* text)
{
    ImGui::TextUnformatted(text);
    ui_dump_table_cell(text, false);
}

inline bool RS_TableCellInputText(const char* label, char* buf, size_t buf_size, ImGuiInputTextFlags flags = 0)
{
    bool result = ImGui::InputText(label, buf, buf_size, flags);
    ui_dump_table_cell(buf, true); // Mark as editable
    return result;
}

inline bool RS_TableCellInputFloat(const char* label, float* v, float step = 0.0f, float step_fast = 0.0f, const char* format = "%.3f", ImGuiInputTextFlags flags = 0)
{
    bool result = ImGui::InputFloat(label, v, step, step_fast, format, flags);
    char value_str[64];
    snprintf(value_str, sizeof(value_str), format, *v);
    ui_dump_table_cell(value_str, true); // Mark as editable
    return result;
}

inline bool RS_TableCellInputDouble(const char* label, double* v, double step = 0.0, double step_fast = 0.0, const char* format = "%.6f", ImGuiInputTextFlags flags = 0)
{
    bool result = ImGui::InputDouble(label, v, step, step_fast, format, flags);
    char value_str[64];
    snprintf(value_str, sizeof(value_str), format, *v);
    ui_dump_table_cell(value_str, true); // Mark as editable
    return result;
}

inline bool RS_BeginTabBar(const char* str_id, ImGuiTabBarFlags flags = 0)
{
    bool result = ImGui::BeginTabBar(str_id, flags);
    if (result) {
        ui_dump_tabbar_begin(str_id);
    }
    return result;
}

inline void RS_EndTabBar()
{
    ui_dump_tabbar_end();
    ImGui::EndTabBar();
}

// Enhanced combo with option tracking
inline bool RS_Combo(const char* label, int* current_item, const char* const items[], int items_count, int popup_max_height_in_items = -1)
{
    bool combo_opened = false;
    bool result = false;

    // Track combo opening
    if (RS_BeginCombo(label, items[*current_item])) {
        combo_opened = true;
        
        for (int i = 0; i < items_count; i++) {
            const bool is_selected = (*current_item == i);
            if (RS_Selectable(items[i], is_selected)) {
                *current_item = i;
                result = true;
            }
            
            if (is_selected) {
                ImGui::SetItemDefaultFocus();
            }
        }
        
        RS_EndCombo();
    }
    
    return result;
}

// Custom widget instrumentation
inline void RS_CustomInteractive(const char* label, const char* type = "custom")
{
    ui_dump_custom_interactive(label, type);
}

// Text and label wrappers
inline void RS_Text(const char* fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    ImGui::TextV(fmt, args);
    va_end(args);
    
    // Create text from format
    char text_buffer[1024];
    va_start(args, fmt);
    vsnprintf(text_buffer, sizeof(text_buffer), fmt, args);
    va_end(args);
    
    ui_dump_on_text(text_buffer);
}

inline void RS_TextUnformatted(const char* text, const char* text_end = NULL)
{
    ImGui::TextUnformatted(text, text_end);
    ui_dump_on_text(text);
}

inline void RS_LabelText(const char* label, const char* fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    ImGui::LabelTextV(label, fmt, args);
    va_end(args);
    
    // Create text from format
    char text_buffer[1024];
    va_start(args, fmt);
    vsnprintf(text_buffer, sizeof(text_buffer), fmt, args);
    va_end(args);
    
    ui_dump_on_label_text(label, text_buffer);
}
