#pragma once

#include <imgui.h>
#include "ui_dump.h"
#include <cstdarg>
#include <functional>

// Enhanced RS_ wrappers for comprehensive UI instrumentation
// All wrappers use stable IDs, normalize labels, and capture control values

// Button widgets
inline bool RS_Button(const char* label, const ImVec2& size = ImVec2(0, 0))
{
    bool result = ImGui::Button(label, size);
    RS_LOG_LAST("button", label);
    ui_set_last([](UiNode& n){ 
        n.actions = {"click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

inline bool RS_SmallButton(const char* label)
{
    bool result = ImGui::SmallButton(label);
    RS_LOG_LAST("button", label);
    ui_set_last([](UiNode& n){ 
        n.actions = {"click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

inline bool RS_ArrowButton(const char* str_id, ImGuiDir dir)
{
    bool result = ImGui::ArrowButton(str_id, dir);
    RS_LOG_LAST("button", str_id);
    ui_set_last([](UiNode& n){ 
        n.actions = {"click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

inline bool RS_ImageButton(ImTextureID texture, const ImVec2& size, const ImVec2& uv0 = ImVec2(0, 0), const ImVec2& uv1 = ImVec2(1, 1), int frame_padding = -1, const ImVec4& bg_col = ImVec4(0, 0, 0, 0), const ImVec4& tint_col = ImVec4(1, 1, 1, 1))
{
    bool result = ImGui::ImageButton(texture, size, uv0, uv1, frame_padding, bg_col, tint_col);
    RS_LOG_LAST("button", "");
    ui_set_last([](UiNode& n){ 
        n.actions = {"click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

// Checkbox and radio buttons
inline bool RS_Checkbox(const char* label, bool* v)
{
    bool result = ImGui::Checkbox(label, v);
    RS_LOG_LAST("checkbox", label);
    ui_set_last([v](UiNode& n){ 
        n.checked = v ? *v : false; 
        n.actions = {"click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

inline bool RS_RadioButton(const char* label, bool active)
{
    bool result = ImGui::RadioButton(label, active);
    RS_LOG_LAST("radio", label);
    ui_set_last([active](UiNode& n){ 
        n.checked = active; 
        n.actions = {"click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

inline bool RS_RadioButton(const char* label, int* v, int v_button)
{
    bool result = ImGui::RadioButton(label, v, v_button);
    RS_LOG_LAST("radio", label);
    ui_set_last([v, v_button](UiNode& n){ 
        n.checked = (v && *v == v_button); 
        n.actions = {"click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

// Selectables
inline bool RS_Selectable(const char* label, bool selected = false, ImGuiSelectableFlags flags = 0, const ImVec2& size = ImVec2(0, 0))
{
    bool result = ImGui::Selectable(label, selected, flags, size);
    RS_LOG_LAST("selectable", label);
    ui_set_last([selected](UiNode& n){ 
        n.state_selected = selected; 
        n.actions = {"click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

inline bool RS_Selectable(const char* label, bool* p_selected, ImGuiSelectableFlags flags = 0, const ImVec2& size = ImVec2(0, 0))
{
    bool result = ImGui::Selectable(label, p_selected, flags, size);
    RS_LOG_LAST("selectable", label);
    ui_set_last([p_selected](UiNode& n){ 
        n.state_selected = p_selected ? *p_selected : false; 
        n.actions = {"click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

// Sliders
inline bool RS_SliderFloat(const char* label, float* v, float v_min, float v_max, const char* format = "%.3f", ImGuiSliderFlags flags = 0)
{
    bool result = ImGui::SliderFloat(label, v, v_min, v_max, format, flags);
    RS_LOG_LAST("slider", label);
    ui_set_last([v, v_min, v_max](UiNode& n){ 
        n.value = v ? *v : 0.0; 
        n.vmin = v_min; 
        n.vmax = v_max; 
        n.actions = {"drag", "click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
        n.track_from = ImVec2(n.min.x, (n.min.y + n.max.y) * 0.5f);
        n.track_to = ImVec2(n.max.x, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

inline bool RS_SliderInt(const char* label, int* v, int v_min, int v_max, const char* format = "%d", ImGuiSliderFlags flags = 0)
{
    bool result = ImGui::SliderInt(label, v, v_min, v_max, format, flags);
    RS_LOG_LAST("slider", label);
    ui_set_last([v, v_min, v_max](UiNode& n){ 
        n.value = v ? *v : 0.0; 
        n.vmin = v_min; 
        n.vmax = v_max; 
        n.actions = {"drag", "click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
        n.track_from = ImVec2(n.min.x, (n.min.y + n.max.y) * 0.5f);
        n.track_to = ImVec2(n.max.x, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

// Drag controls
inline bool RS_DragFloat(const char* label, float* v, float v_speed = 1.0f, float v_min = 0.0f, float v_max = 0.0f, const char* format = "%.3f", ImGuiSliderFlags flags = 0)
{
    bool result = ImGui::DragFloat(label, v, v_speed, v_min, v_max, format, flags);
    RS_LOG_LAST("drag", label);
    ui_set_last([v, v_min, v_max](UiNode& n){ 
        n.value = v ? *v : 0.0; 
        n.vmin = v_min; 
        n.vmax = v_max; 
        n.actions = {"drag", "click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

inline bool RS_DragInt(const char* label, int* v, float v_speed = 1.0f, int v_min = 0, int v_max = 0, const char* format = "%d", ImGuiSliderFlags flags = 0)
{
    bool result = ImGui::DragInt(label, v, v_speed, v_min, v_max, format, flags);
    RS_LOG_LAST("drag", label);
    ui_set_last([v, v_min, v_max](UiNode& n){ 
        n.value = v ? *v : 0.0; 
        n.vmin = v_min; 
        n.vmax = v_max; 
        n.actions = {"drag", "click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

// Input controls
inline bool RS_InputText(const char* label, char* buf, size_t buf_size, ImGuiInputTextFlags flags = 0, ImGuiInputTextCallback callback = NULL, void* user_data = NULL)
{
    bool result = ImGui::InputText(label, buf, buf_size, flags, callback, user_data);
    RS_LOG_LAST("input_text", label);
    ui_set_last([buf](UiNode& n){ 
        n.text_value = std::string(buf ? buf : ""); 
        n.actions = {"type"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

inline bool RS_InputInt(const char* label, int* v, int step = 1, int step_fast = 100, ImGuiInputTextFlags flags = 0)
{
    bool result = ImGui::InputInt(label, v, step, step_fast, flags);
    RS_LOG_LAST("input_int", label);
    ui_set_last([v, step](UiNode& n){ 
        n.value = v ? *v : 0.0; 
        n.vstep = step; 
        n.actions = {"type"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

inline bool RS_InputFloat(const char* label, float* v, float step = 0.0f, float step_fast = 0.0f, const char* format = "%.3f", ImGuiInputTextFlags flags = 0)
{
    bool result = ImGui::InputFloat(label, v, step, step_fast, format, flags);
    RS_LOG_LAST("input_float", label);
    ui_set_last([v, step](UiNode& n){ 
        n.value = v ? *v : 0.0; 
        n.vstep = step; 
        n.actions = {"type"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

inline bool RS_InputDouble(const char* label, double* v, double step = 0.0, double step_fast = 0.0, const char* format = "%.6f", ImGuiInputTextFlags flags = 0)
{
    bool result = ImGui::InputDouble(label, v, step, step_fast, format, flags);
    RS_LOG_LAST("input_double", label);
    ui_set_last([v, step](UiNode& n){ 
        n.value = v ? *v : 0.0; 
        n.vstep = step; 
        n.actions = {"type"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

// Combo controls
inline bool RS_BeginCombo(const char* label, const char* preview_value, ImGuiComboFlags flags = 0)
{
    bool result = ImGui::BeginCombo(label, preview_value, flags);
    if (result) {
        ui_dump_combo_begin(label, preview_value);
        ui_set_last([preview_value](UiNode& n){ 
            n.selected_value = preview_value ? preview_value : ""; 
            n.actions = {"open", "select"}; 
            n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
        });
    } else {
        // Log the combo even when closed - this ensures dropdowns are always visible
        ui_dump_combo_closed(label, preview_value);
        ui_set_last([preview_value](UiNode& n){ 
            n.selected_value = preview_value ? preview_value : ""; 
            n.actions = {"open", "select"}; 
            n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
        });
    }
    return result;
}

inline void RS_EndCombo()
{
    ui_dump_combo_end();
    ImGui::EndCombo();
}

inline bool RS_Combo(const char* label, int* current_item, const char* const items[], int items_count, int popup_max_height_in_items = -1)
{
    bool result = ImGui::Combo(label, current_item, items, items_count, popup_max_height_in_items);
    RS_LOG_LAST("combo", label);
    ui_set_last([current_item, items, items_count](UiNode& n){ 
        if (current_item && *current_item >= 0 && *current_item < items_count) {
            n.selected_value = items[*current_item];
        }
        n.actions = {"open", "select"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
        for (int i = 0; i < items_count; i++) {
            n.options.push_back(items[i]);
        }
    });
    return result;
}

// Color controls
inline bool RS_ColorEdit3(const char* label, float col[3], ImGuiColorEditFlags flags = 0)
{
    bool result = ImGui::ColorEdit3(label, col, flags);
    RS_LOG_LAST("color", label);
    ui_set_last([](UiNode& n){ 
        n.actions = {"click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

inline bool RS_ColorEdit4(const char* label, float col[4], ImGuiColorEditFlags flags = 0)
{
    bool result = ImGui::ColorEdit4(label, col, flags);
    RS_LOG_LAST("color", label);
    ui_set_last([](UiNode& n){ 
        n.actions = {"click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

// Menu controls
inline bool RS_BeginMenu(const char* label, bool enabled = true)
{
    bool result = ImGui::BeginMenu(label, enabled);
    if (result) {
        ImGuiID menu_id = ImGui::GetItemID();
        ui_dump_on_begin_popup(label, (uint64_t)menu_id);
    }
    RS_LOG_LAST("menu", label);
    ui_set_last([enabled](UiNode& n){ 
        n.enabled = enabled; 
        n.actions = {"open"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
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
    RS_LOG_LAST("menu", label);
    ui_set_last([selected, enabled](UiNode& n){ 
        n.state_selected = selected; 
        n.enabled = enabled; 
        n.actions = {"click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

inline bool RS_MenuItem(const char* label, const char* shortcut, bool* p_selected, bool enabled = true)
{
    bool result = ImGui::MenuItem(label, shortcut, p_selected, enabled);
    RS_LOG_LAST("menu", label);
    ui_set_last([p_selected, enabled](UiNode& n){ 
        n.state_selected = p_selected ? *p_selected : false; 
        n.enabled = enabled; 
        n.actions = {"click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

// Tree controls
inline bool RS_TreeNode(const char* label)
{
    bool result = ImGui::TreeNode(label);
    RS_LOG_LAST("header", label);
    ui_set_last([result](UiNode& n){ 
        n.state_open = result; 
        n.actions = {"click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

inline bool RS_TreeNodeEx(const char* label, ImGuiTreeNodeFlags flags = 0)
{
    bool result = ImGui::TreeNodeEx(label, flags);
    RS_LOG_LAST("header", label);
    ui_set_last([result](UiNode& n){ 
        n.state_open = result; 
        n.actions = {"click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

inline void RS_TreePop()
{
    ImGui::TreePop();
}

// Collapsing header
inline bool RS_CollapsingHeader(const char* label, ImGuiTreeNodeFlags flags = 0)
{
    bool result = ImGui::CollapsingHeader(label, flags);
    RS_LOG_LAST("header", label);
    ui_set_last([result](UiNode& n){ 
        n.state_open = result; 
        n.actions = {"click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

inline bool RS_CollapsingHeader(const char* label, bool* p_visible, ImGuiTreeNodeFlags flags = 0)
{
    bool result = ImGui::CollapsingHeader(label, p_visible, flags);
    RS_LOG_LAST("header", label);
    ui_set_last([result, p_visible](UiNode& n){ 
        n.state_open = result; 
        n.visible = p_visible ? *p_visible : true; 
        n.actions = {"click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

// Custom interactive elements
inline void RS_LogCustomInteractive(const char* label, const char* type, const ImRect& bb)
{
    ImGui::ItemAdd(bb, ImGui::GetID(label));
    RS_LOG_LAST("custom", label);
    ui_set_last([type](UiNode& n){ 
        n.type = type; 
        n.actions = {"click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
}

// Progress bar
inline void RS_ProgressBar(float fraction, const ImVec2& size_arg = ImVec2(-FLT_MIN, 0), const char* overlay = NULL)
{
    ImGui::ProgressBar(fraction, size_arg, overlay);
    RS_LOG_LAST("progress", overlay ? overlay : "");
    ui_set_last([fraction](UiNode& n){ 
        n.value = fraction; 
        n.vmin = 0.0; 
        n.vmax = 1.0; 
    });
}

// Text
inline void RS_Text(const char* fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    ImGui::TextV(fmt, args);
    va_end(args);
    RS_LOG_LAST("label", fmt);
}

inline void RS_TextColored(const ImVec4& col, const char* fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    ImGui::TextColoredV(col, fmt, args);
    va_end(args);
    RS_LOG_LAST("label", fmt);
}

inline void RS_TextDisabled(const char* fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    ImGui::TextDisabledV(fmt, args);
    va_end(args);
    RS_LOG_LAST("label", fmt);
    ui_set_last([](UiNode& n){ n.enabled = false; });
}

inline void RS_TextWrapped(const char* fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    ImGui::TextWrappedV(fmt, args);
    va_end(args);
    RS_LOG_LAST("label", fmt);
}

inline void RS_LabelText(const char* label, const char* fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    ImGui::LabelTextV(label, fmt, args);
    va_end(args);
    RS_LOG_LAST("label", label);
}

// Tab controls
inline bool RS_BeginTabBar(const char* str_id, ImGuiTabBarFlags flags = 0)
{
    bool result = ImGui::BeginTabBar(str_id, flags);
    ui_dump_tabbar_begin(str_id);
    return result;
}

inline void RS_EndTabBar()
{
    ui_dump_tabbar_end();
    ImGui::EndTabBar();
}

inline bool RS_BeginTabItem(const char* label, bool* p_open = NULL, ImGuiTabItemFlags flags = 0)
{
    bool result = ImGui::BeginTabItem(label, p_open, flags);
    ui_dump_on_tabitem(label, result);
    ui_set_last([result, p_open](UiNode& n){ 
        n.state_selected = result; 
        n.visible = p_open ? *p_open : true; 
        n.actions = {"click"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

inline void RS_EndTabItem()
{
    ImGui::EndTabItem();
}

// Table cell helpers
inline bool RS_TableCellInputFloat(const char* label, float* v, float step = 0.0f, float step_fast = 0.0f, const char* format = "%.3f", ImGuiInputTextFlags flags = 0)
{
    bool result = ImGui::InputFloat(label, v, step, step_fast, format, flags);
    ui_dump_table_cell(label, true);
    ui_set_last([v, step](UiNode& n){ 
        n.value = v ? *v : 0.0; 
        n.vstep = step; 
        n.actions = {"type"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

inline bool RS_TableCellInputDouble(const char* label, double* v, double step = 0.0, double step_fast = 0.0, const char* format = "%.6f", ImGuiInputTextFlags flags = 0)
{
    bool result = ImGui::InputDouble(label, v, step, step_fast, format, flags);
    ui_dump_table_cell(label, true);
    ui_set_last([v, step](UiNode& n){ 
        n.value = v ? *v : 0.0; 
        n.vstep = step; 
        n.actions = {"type"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

inline bool RS_TableCellInputText(const char* label, char* buf, size_t buf_size, ImGuiInputTextFlags flags = 0)
{
    bool result = ImGui::InputText(label, buf, buf_size, flags);
    ui_dump_table_cell(label, true);
    ui_set_last([buf](UiNode& n){ 
        n.text_value = std::string(buf ? buf : ""); 
        n.actions = {"type"}; 
        n.action_point = ImVec2((n.min.x + n.max.x) * 0.5f, (n.min.y + n.max.y) * 0.5f);
    });
    return result;
}

#ifdef RS_DUMP_UI
#  define RS_LOG_LAST(TYPE, LABEL) ui_dump_on_item_committed(TYPE, LABEL)
#else
#  define RS_LOG_LAST(TYPE, LABEL) do{}while(0)
#endif
