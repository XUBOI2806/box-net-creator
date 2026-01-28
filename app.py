import streamlit as st
import subprocess
import tempfile
from pathlib import Path

import sys
from pathlib import Path
import shutil

def get_inkscape_path():
    # 1. If running as a bundled EXE (PyInstaller)
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
        bundled = base / "resources" / "Inkscape" / "bin" / "inkscape.exe"
        if bundled.exists():
            return str(bundled)

    # 2. If running from source
    dev_path = Path(__file__).parent / "resources" / "Inkscape" / "bin" / "inkscape.exe"
    if dev_path.exists():
        return str(dev_path)

    # 3. Fallback to system PATH
    system = shutil.which("inkscape")
    if system:
        return system

    return None

INKSCAPE = get_inkscape_path()

if not INKSCAPE:
    st.error(
        "Inkscape not found.\n\n"
        "Please make sure the 'resources/Inkscape' folder is present or Inkscape is installed system-wide."
    )
    st.stop()

def tab_size(value, base):
    if value == "H":
        return base * 2
    return base

# ---------- SVG GENERATOR ----------
def generate_box_sheet_svg(boxes, spacing=1000, scale=0.1, left_margin=100):
    def rect(x, y, w, h, stroke="red"):
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{stroke}" stroke-width="1"/>'

    def polygon(points, stroke="red"):
        pts_str = " ".join([f"{x},{y}" for x, y in points])
        return f'<polygon points="{pts_str}" fill="none" stroke="{stroke}" stroke-width="1"/>'

    def text(x, y, value, size=20, color="red", rotate=0):
        transform = f' transform="rotate({rotate},{x},{y})"' if rotate != 0 else ""
        return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="middle" alignment-baseline="middle"{transform}>{value}</text>'

    def line(x1, y1, x2, y2, color="red", stroke_width=1):
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{stroke_width}" />'

    def tab_size(value, base):
        if value == "H":
            return base * 2
        return base

    # --- Tab polygons for Bottom-Right L-shape ---
    def tabs_for_bottom_right(base_x, base_y, width, length, ext_w, ext_l, top_tab, bottom_tab, left_tab, right_tab):
        elements = []

        # Top tab (only main rectangle width)
        top_poly = [
            (base_x, base_y - top_tab),
            (base_x + width, base_y - top_tab),
            (base_x + width, base_y),
            (base_x, base_y)
        ]
        elements.append(polygon(top_poly))

        # Bottom tab (along bottom leg)
        bottom_poly = [
            (base_x, base_y + length),
            (base_x + width + ext_w, base_y + length),
            (base_x + width + ext_w, base_y + length + bottom_tab),
            (base_x, base_y + length + bottom_tab)
        ]
        elements.append(polygon(bottom_poly))

        # Left tab
        left_poly = [
            (base_x - left_tab, base_y),
            (base_x, base_y),
            (base_x, base_y + length),
            (base_x - left_tab, base_y + length)
        ]
        elements.append(polygon(left_poly))

        # Right tab polygon (correct wrapping)
        rt = right_tab
        right_poly = [
            # Top vertical segment of rectangle
            (base_x + width, base_y),                # top-left
            (base_x + width + rt, base_y),          # top-right
            (base_x + width + rt, base_y + length - ext_l - rt), # bottom-right of vertical segment
            (base_x + width + rt + ext_w, base_y + length - ext_l - rt),   # bottom-left of vertical segment
            (base_x + width + rt + ext_w, base_y + length), # bottom-left of horizontal extension
            (base_x + width + rt, base_y + length),
            (base_x + width + rt, base_y + length - ext_l),
            (base_x + width, base_y + length - ext_l)
            
        ]
        elements.append(polygon(right_poly))

        return elements

    # --- Layout ---
    max_left_tab = max([tab_size(box.get("left"), box["side"]) for box in boxes] or [0])
    shift_x = max_left_tab + left_margin
    elements = []
    x_offset = 0
    y_offset = 0
    max_row_height = 0
    columns = 4
    row_widths = []

    for i, box in enumerate(boxes):
        width = box["width"] * scale
        length = box["length"] * scale
        side = box["side"] * scale
        label = box["label"]

        top_tab = tab_size(box.get("up"), side)
        bottom_tab = tab_size(box.get("down"), side)
        left_tab = tab_size(box.get("left"), side)
        right_tab = tab_size(box.get("right"), side)

        base_x = x_offset + 50
        base_y = y_offset + 2 * side + 20

        # --- Main polygon (rectangle or L-shape) ---
        if box.get("is_lshape"):
            ext_w = box["ext_width"] * scale
            ext_l = box["ext_length"] * scale
            orientation = box.get("orientation", "Bottom-Right")

            if orientation == "Bottom-Right":
                main_pts = [
                    (base_x, base_y),
                    (base_x + width, base_y),
                    (base_x + width, base_y + length - ext_l),
                    (base_x + width + ext_w, base_y + length - ext_l),
                    (base_x + width + ext_w, base_y + length),
                    (base_x, base_y + length)
                ]
                # Draw tabs
                tabs = tabs_for_bottom_right(base_x, base_y, width, length, ext_w, ext_l,
                                             top_tab, bottom_tab, left_tab, right_tab)
                elements.extend(tabs)
            # Draw main polygon
                elements.append(polygon(main_pts))
        else:
            main_pts = [
                    (base_x, base_y),
                    (base_x + width, base_y),
                    (base_x + width, base_y + length),
                    (base_x, base_y + length)
                ]
            elements += [
            rect(base_x, base_y, width, length),
            rect(base_x, base_y - top_tab, width, top_tab),           # top
            rect(base_x, base_y + length, width, bottom_tab),         # bottom
            rect(base_x - left_tab, base_y, left_tab, length),        # left
            rect(base_x + width, base_y, right_tab, length),          # right
            ]

        # --- Label inside the box ---
        elements.append(text(base_x + width / 2, 2 * (base_y + length) / 3, label, 60*scale, "blue"))

        # --- Middle arrow inside main rectangle ---
        center_x = base_x + width / 2
        center_y = base_y + length / 2
        arrow_length = 300 * scale
        arrow_head_size = 30 * scale
        line_end_y = center_y - arrow_length + arrow_head_size
        elements.append(f'<line x1="{center_x}" y1="{center_y}" x2="{center_x}" y2="{line_end_y}" stroke="red" stroke-width="1"/>')
        elements.append(f'<polygon points="{center_x},{line_end_y - arrow_head_size} {center_x - arrow_head_size},{line_end_y} {center_x + arrow_head_size},{line_end_y}" fill="red"/>')

        # --- Direction inputs inside the box ---
        if box.get("up") and box["up"] != "None":
            elements.append(text(base_x + width/2, base_y + length*0.25, box["up"], 50*scale, "red"))
        if box.get("down") and box["down"] != "None":
            elements.append(text(base_x + width/2, base_y + length*0.75, box["down"], 50*scale, "red"))
        if box.get("left") and box["left"] != "None":
            elements.append(text(base_x + width*0.25, base_y + length/2, box["left"], 50*scale, "red"))
        if box.get("right") and box["right"] != "None":
            elements.append(text(base_x + width*0.75, base_y + length/2, box["right"], 50*scale, "red"))

        # --- Bottom measurement line ---
        if box.get("is_lshape"): 
            y_bottom = base_y + length + bottom_tab + side
            elements.append(line(base_x, y_bottom, base_x + width + ext_w, y_bottom))
            elements.append(line(base_x, y_bottom - 3, base_x, y_bottom + 3))
            elements.append(line(base_x + width + ext_w, y_bottom - 3, base_x + width + ext_w, y_bottom + 3))
            elements.append(f'<polygon points="{base_x},{y_bottom} {base_x+5},{y_bottom-3} {base_x+5},{y_bottom+3}" fill="red"/>')
            elements.append(f'<polygon points="{base_x+width+ext_w},{y_bottom} {base_x+width+ext_w-5},{y_bottom-3} {base_x+width+ext_w-5},{y_bottom+3}" fill="red"/>')
            elements.append(text(base_x + (width + ext_w)/2, y_bottom + 10*scale + 7, f"{int(width + ext_w)} mm", 90*scale))

            # --- Right measurement line (main vertical leg) ---
            x_right = base_x + width + ext_w + right_tab + side
            y_top = base_y
            y_bottom_leg = base_y + length - ext_l

            elements.append(line(x_right, y_top, x_right, y_bottom_leg))
            elements.append(line(x_right - 3, y_top, x_right + 3, y_top))
            elements.append(line(x_right - 3, y_bottom_leg, x_right + 3, y_bottom_leg))
            elements.append(f'<polygon points="{x_right},{y_top} {x_right-3},{y_top+5} {x_right+3},{y_top+5}" fill="red"/>')
            elements.append(f'<polygon points="{x_right},{y_bottom_leg} {x_right-3},{y_bottom_leg-5} {x_right+3},{y_bottom_leg-5}" fill="red"/>')
            elements.append(
                text(
                    x_right + 20*scale,
                    (y_top + y_bottom_leg) / 2,
                    f"{int(length - ext_l)} mm",
                    90*scale,
                    rotate=90
                )
            )

            # --- Up measurement line (extension vertical leg) ---
            x_ext = base_x + width + ext_w + right_tab + side
            y_ext_top = base_y + length - ext_l
            y_ext_bottom = base_y + length

            elements.append(line(x_ext, y_ext_top, x_ext, y_ext_bottom))
            elements.append(line(x_ext - 3, y_ext_top, x_ext + 3, y_ext_top))
            elements.append(line(x_ext - 3, y_ext_bottom, x_ext + 3, y_ext_bottom))
            elements.append(
                text(
                    x_ext + 30*scale,
                    (y_ext_top + y_ext_bottom) / 2,
                    f"{int(ext_l)} mm",
                    90*scale,
                    rotate=90
                )
            )

            # --- Top width measurement line ---
            y_top = base_y - top_tab - side
            elements.append(line(base_x, y_top, base_x + width, y_top))
            elements.append(line(base_x, y_top - 3, base_x, y_top + 3))
            elements.append(line(base_x + width, y_top - 3, base_x + width, y_top + 3))
            elements.append(f'<polygon points="{base_x},{y_top} {base_x+5},{y_top-3} {base_x+5},{y_top+3}" fill="red"/>')
            elements.append(f'<polygon points="{base_x+width},{y_top} {base_x+width-5},{y_top-3} {base_x+width-5},{y_top+3}" fill="red"/>')
            elements.append(
                text(
                    base_x + width/2,
                    y_top - 10*scale - 7,
                    f"{int(width)} mm",
                    90*scale
                )
            )

        else:
            y_bottom = base_y + length + bottom_tab + side
            elements.append(line(base_x, y_bottom, base_x + width, y_bottom))
            elements.append(line(base_x, y_bottom - 3, base_x, y_bottom + 3))
            elements.append(line(base_x + width, y_bottom - 3, base_x + width, y_bottom + 3))
            elements.append(f'<polygon points="{base_x},{y_bottom} {base_x+5},{y_bottom-3} {base_x+5},{y_bottom+3}" fill="red"/>')
            elements.append(f'<polygon points="{base_x+width},{y_bottom} {base_x+width-5},{y_bottom-3} {base_x+width-5},{y_bottom+3}" fill="red"/>')
            elements.append(text(base_x + width/2, y_bottom + 10*scale + 7, f"{int(box['width'])} mm", 90*scale))
        
        # --- Left measurement line ---
        x_left = base_x - left_tab - side
        elements.append(line(x_left, base_y, x_left, base_y + length))
        elements.append(line(x_left - 3, base_y, x_left + 3, base_y))
        elements.append(line(x_left - 3, base_y + length, x_left + 3, base_y + length))
        elements.append(f'<polygon points="{x_left},{base_y} {x_left-3},{base_y+5} {x_left+3},{base_y+5}" fill="red"/>')
        elements.append(f'<polygon points="{x_left},{base_y+length} {x_left-3},{base_y+length-5} {x_left+3},{base_y+length-5}" fill="red"/>')
        elements.append(text(x_left - 10*scale, base_y + length/2, f"{int(length)} mm", 90*scale, rotate=270))
        
        # Update layout
        xs, ys = zip(*main_pts)
        net_w = max(xs) - min(xs) + left_tab + right_tab
        net_h = max(ys) - min(ys) + top_tab + bottom_tab
        max_row_height = max(max_row_height, net_h)

        if (i + 1) % columns == 0:
            row_widths.append(x_offset + net_w)
            x_offset = 0
            y_offset += max_row_height + spacing*scale
            max_row_height = 0
        else:
            x_offset += net_w + spacing*scale

    if len(boxes) % columns != 0:
        row_widths.append(x_offset if x_offset > 0 else 0)

    canvas_width = max(row_widths) + shift_x
    canvas_height = y_offset + max_row_height + spacing*scale

    return f"""
<svg xmlns="http://www.w3.org/2000/svg"
     width="{canvas_width}mm"
     height="{canvas_height}mm"
     viewBox="0 0 {canvas_width} {canvas_height}">
    {''.join(elements)}
</svg>
"""



# ---------- PDF GENERATION (SAFE) ----------
def generate_pdf_bytes(svg_text: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        svg_path = tmp / "box_sheet.svg"
        pdf_path = tmp / "box_sheet.pdf"

        svg_path.write_text(svg_text)

        subprocess.run([
            INKSCAPE,
            str(svg_path),
            "--export-type=pdf",
            "--export-filename", str(pdf_path)
        ], check=True)

        return pdf_path.read_bytes()


# ---------- STREAMLIT UI ----------
st.set_page_config(layout="wide")
st.title("📦 Box Net Creator - Inkscape Preview")

if "boxes" not in st.session_state:
    st.session_state.boxes = []


st.subheader("Edit / Add Box")

if st.session_state.boxes:
    box_names = [
        f"{i+1}. {b['label']} ({int(b['width'])}×{int(b['length'])})"
        for i, b in enumerate(st.session_state.boxes)
    ]
    selected_index = st.selectbox(
        "Select box to edit",
        options=[None] + list(range(len(box_names))),
        format_func=lambda x: "➕ New Box" if x is None else box_names[x]
    )
else:
    selected_index = None

selected_box = (
    st.session_state.boxes[selected_index]
    if selected_index is not None
    else None
)


is_lshape = st.checkbox(
    "L-shape",
    value=selected_box["is_lshape"] if selected_box else True
)

with st.form("Box Form"):
    col_w, col_l, col_s, col_lab = st.columns(4)
    with col_w:
        width = st.number_input(
            "Width (mm)", 100.0, 5000.0,
            value=selected_box["width"] if selected_box else 1442.0
        )
    with col_l:
        length = st.number_input(
            "Length (mm)", 100.0, 5000.0,
            value=selected_box["length"] if selected_box else 2488.0
        )
    with col_s:
        side = st.number_input(
            "Side / Tab size (mm)", 10.0, 500.0,
            value=selected_box["side"] if selected_box else 100.0
        )
    with col_lab:
        label_input = st.text_input(
            "Label",
            value=selected_box["label"] if selected_box else ""
        )

    col_up, col_down, col_left, col_right = st.columns(4)
    option_values = ["None", "S", "SS", "L", "H"]
    with col_up:
        up_val = st.selectbox(
            "Up", option_values,
            index=option_values.index(selected_box["up"]) if selected_box else 0
        )
    with col_down:
        down_val = st.selectbox(
            "Down", option_values,
            index=option_values.index(selected_box["down"]) if selected_box else 0
        )
    with col_left:
        left_val = st.selectbox(
            "Left", option_values,
            index=option_values.index(selected_box["left"]) if selected_box else 0
        )
    with col_right:
        right_val = st.selectbox(
            "Right", option_values,
            index=option_values.index(selected_box["right"]) if selected_box else 0
        )

    if is_lshape:
        ext_width = st.number_input(
            "Extension Width (mm)", 10.0, 1000.0,
            value=selected_box["ext_width"] if selected_box else 100.0
        )
        ext_length = st.number_input(
            "Extension Length (mm)", 10.0, 1000.0,
            value=selected_box["ext_length"] if selected_box else 100.0
        )
    else:
        ext_width = ext_length = 0

    col_save, col_delete = st.columns(2)
    save_btn = st.form_submit_button("💾 Save")
    delete_btn = st.form_submit_button("🗑️ Delete")

    if save_btn:
        box_data = {
            "width": width,
            "length": length,
            "side": side,
            "label": label_input,
            "up": up_val,
            "down": down_val,
            "left": left_val,
            "right": right_val,
            "is_lshape": is_lshape,
            "ext_width": ext_width,
            "ext_length": ext_length,
        }

        if selected_index is None:
            # ➕ New box
            st.session_state.boxes.append(box_data)
        else:
            # ✏️ Update existing box
            st.session_state.boxes[selected_index] = box_data

        st.rerun()

    if delete_btn and selected_index is not None:
        st.session_state.boxes.pop(selected_index)
        st.rerun()


# --- Show added boxes ---
st.subheader("Boxes Added")
for i, box in enumerate(st.session_state.boxes):
    st.write(f"{i+1}. {box['label']} - {box['width']}x{box['length']} mm, Side: {box['side']} mm, Up:{box['up']} Down:{box['down']} Left:{box['left']} Right:{box['right']}")

# --- Clear all boxes ---
if st.button("🗑️ Clear All Boxes"):
    st.session_state.boxes = []

# --- Generate SVG + Preview ---
if st.session_state.boxes:
    svg = generate_box_sheet_svg(st.session_state.boxes, scale=0.1, left_margin=30)

    st.subheader("Preview")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        svg_path = tmp / "preview.svg"
        png_path = tmp / "preview.png"

        svg_path.write_text(svg)

        subprocess.run([
            INKSCAPE,
            str(svg_path),
            "--export-type=png",
            "--export-filename", str(png_path)
        ], check=True)

        st.image(str(png_path))

    pdf_bytes = generate_pdf_bytes(svg)

    st.download_button(
        "⬇️ Generate & Download PDF",
        data=pdf_bytes,
        file_name="box_sheet.pdf",
        mime="application/pdf"
    )