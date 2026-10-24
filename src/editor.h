#pragma once
#include "common.h"

namespace app {

struct AnnotationItem {
    std::wstring tool;
    std::wstring color;
    int size = 5;
    int stroke_px = 5;
    std::vector<Gdiplus::Point> points;
    std::wstring text;
    int font_px = 24;

    void Translate(int dx, int dy, int max_w, int max_h);
    Gdiplus::Rect GetBBox() const;
    std::vector<Gdiplus::Point> GetHandles() const;
    void MoveHandle(int handle_idx, int new_x, int new_y);
    bool HitTest(int ix, int iy, int base_tol = 14) const;
};

class AnnotationEditor {
public:
    using OnCopyClipboard = std::function<void(Gdiplus::Bitmap*)>;
    using OnClose = std::function<void()>;

    AnnotationEditor(
        std::unique_ptr<Gdiplus::Bitmap> image,
        OnCopyClipboard on_copy_clipboard,
        OnClose on_close);
    ~AnnotationEditor();

    void CloseEditor();
    bool IsOpen() const { return hwnd_ != nullptr && IsWindow(hwnd_); }

private:
    static LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam);
    static LRESULT CALLBACK TextEditSubclassProc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam);
    LRESULT HandleMessage(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam);

    enum class BtnKind {
        Tool,
        ActionUndo,
        ActionRedo,
        ActionClear,
        ColorSwatch,
        CustomColor,
        StrokeSize,
        ActionCopy,
        ActionSave,
        ActionClose,
        LabelOnly,
        Divider
    };

    struct ToolbarItem {
        BtnKind kind;
        std::wstring id;
        std::wstring label;
        std::wstring icon_name;
        std::wstring color_hex;
        int size_val = 0;
        int dot_r_pt = 0;
        float req_w = 0.0f;
        float req_h = 0.0f;
        float gap_x = 6.0f;
        Gdiplus::RectF rect{};
        bool visible = true;
    };

    void InitToolbarItems();
    float LayoutFlowRow(std::vector<ToolbarItem>& row_items, float start_y, float total_width, float pad_x, float pad_y, float row_gap);
    void RecalculateLayout(int client_w, int client_h);

    void SelectTool(const std::wstring& tool_id);
    void SelectColor(const std::wstring& hex_color);
    void PickCustomColor();
    void SelectSize(int size_val);
    int ScaledStrokeWidth(int size_override = -1) const;
    int ScaledFontPx(int size_override = -1) const;

    void SaveUndoSnapshot();
    void Undo();
    void Redo();
    void ClearAll();
    void DeleteSelected();
    void CopyAndFinish();
    void SaveToFile();

    Gdiplus::Point CanvasToImageCoords(int cx, int cy) const;
    Gdiplus::PointF ImageToCanvasCoords(float ix, float iy) const;
    int FindHandleAt(int ix, int iy) const;
    int FindItemAt(int ix, int iy) const;

    void SpawnTextEntry(int canvas_x, int canvas_y, const std::wstring& initial_text = L"");
    void CommitActiveText();
    void CancelActiveText();

    void RebuildComposite();
    static std::unique_ptr<Gdiplus::Bitmap> CloneBitmap(Gdiplus::Bitmap* src);
    static std::unique_ptr<Gdiplus::Bitmap> RenderItemsOnto(
        Gdiplus::Bitmap* base,
        const std::vector<AnnotationItem>& items_to_draw);
    static void DrawSingleItem(
        Gdiplus::Graphics& g,
        Gdiplus::Bitmap* pixelate_source,
        const AnnotationItem& item);
    static void DrawProArrow(
        Gdiplus::Graphics& g,
        float x1,
        float y1,
        float x2,
        float y2,
        Gdiplus::Color color,
        float width);

    void RenderWindow(HDC hdc, int client_w, int client_h);
    void DrawToolbarItem(Gdiplus::Graphics& g, const ToolbarItem& item, bool hovered, float dpi);

    HWND hwnd_ = nullptr;
    HWND hwnd_edit_ = nullptr;
    WNDPROC orig_edit_proc_ = nullptr;
    HFONT edit_hfont_ = nullptr;
    HBRUSH edit_bg_brush_ = nullptr;
    int editing_item_idx_ = -1;
    Gdiplus::Point text_img_pos_{0, 0};

    std::unique_ptr<Gdiplus::Bitmap> base_image_;
    std::unique_ptr<Gdiplus::Bitmap> cached_composite_;
    std::unique_ptr<Gdiplus::Bitmap> drag_bg_image_;

    OnCopyClipboard on_copy_clipboard_;
    OnClose on_close_;

    std::vector<AnnotationItem> items_;
    std::vector<std::vector<AnnotationItem>> undo_stack_;
    std::vector<std::vector<AnnotationItem>> redo_stack_;
    int selected_idx_ = -1;

    std::wstring current_tool_ = L"arrow";
    std::wstring current_color_ = L"#ef4444";
    int current_size_ = 5;
    COLORREF custom_colors_[16] = {0};

    enum class InteractionMode {
        None,
        Drawing,
        Moving,
        Handle
    };
    InteractionMode interaction_mode_ = InteractionMode::None;
    int active_handle_idx_ = -1;
    Gdiplus::Point drag_last_img_pos_{0, 0};
    AnnotationItem drawing_item_;

    std::vector<ToolbarItem> row1_items_;
    std::vector<ToolbarItem> row2_items_;
    int hovered_row_ = 0; // 1 or 2
    int hovered_idx_ = -1;

    float row1_h_ = 48.0f;
    float row2_h_ = 46.0f;
    float status_h_ = 30.0f;
    Gdiplus::RectF canvas_area_rc_{};
    Gdiplus::RectF canvas_rc_{};
    float display_scale_x_ = 1.0f;
    float display_scale_y_ = 1.0f;
    int min_win_w_ = 760;
    int min_win_h_ = 480;
    bool closing_ = false;
};

} // namespace app
