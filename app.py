import streamlit as st
import subprocess
import tempfile
from pathlib import Path

# ---------- SVG GENERATOR ----------
def generate_box_sheet_svg(boxes, spacing=1000, scale=0.1, left_margin=100):
    def rect(x, y, w, h, stroke="red"):
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{stroke}" stroke-width="1"/>'

    def text(x, y, value, size=20, color="red", rotate=0):
        transform = f' transform="rotate({rotate},{x},{y})"' if rotate != 0 else ""
        return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="middle" alignment-baseline="middle"{transform}>{value}</text>'

    def line(x1, y1, x2, y2, color="red", stroke_width=1):
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{stroke_width}" />'

    elements = []

    x_offset = left_margin
    y_offset = 0
    max_row_height = 0
    columns = 4
    row_widths = []

    for i, box in enumerate(boxes):
        width = box["width"] * scale
        length = box["length"] * scale
        side = box["side"] * scale
        label = box["label"]

        net_w = width + 2 * side
        net_h = length + 3 * side

        base_x = x_offset
        base_y = y_offset + 2 * side

        # --- Box + tabs ---
        elements += [
            rect(base_x, base_y, width, length),
            rect(base_x, base_y - side, width, side),
            rect(base_x, base_y + length, width, side),
            rect(base_x - side, base_y, side, length),
            rect(base_x + width, base_y, side, length),
            text(base_x + width / 2, 2*(base_y + length) / 3, label, 60*scale, "blue")
        ]

        # --- Middle arrow pointing up from center ---
        center_x = base_x + width / 2
        center_y = base_y + length / 2
        arrow_length = 300 * scale  # tail length
        arrow_head_size = 30 * scale

        # Tail (line from center upwards, stopping before arrowhead)
        line_end_y = center_y - arrow_length + arrow_head_size
        elements.append(f'<line x1="{center_x}" y1="{center_y}" x2="{center_x}" y2="{line_end_y}" stroke="red" stroke-width="1"/>')

        # Arrowhead
        elements.append(f'<polygon points="{center_x},{line_end_y - arrow_head_size} {center_x - arrow_head_size},{line_end_y} {center_x + arrow_head_size},{line_end_y}" fill="red"/>')

        # --- Inputs inside the box ---
        # Up
        if box.get("up") and box["up"] != "None":
            elements.append(text(base_x + width/2, base_y + length*0.25, box["up"], 50*scale, "red"))
        # Down
        if box.get("down") and box["down"] != "None":
            elements.append(text(base_x + width/2, base_y + length*0.75, box["down"], 50*scale, "red"))
        # Left
        if box.get("left") and box["left"] != "None":
            elements.append(text(base_x + width*0.25, base_y + length/2, box["left"], 50*scale, "red"))
        # Right
        if box.get("right") and box["right"] != "None":
            elements.append(text(base_x + width*0.75, base_y + length/2, box["right"], 50*scale, "red"))

        # --- Bottom measurement line ---
        y_bottom = base_y + length + 2*side
        elements.append(line(base_x, y_bottom, base_x + width, y_bottom))
        elements.append(line(base_x, y_bottom - 3, base_x, y_bottom + 3))
        elements.append(line(base_x + width, y_bottom - 3, base_x + width, y_bottom + 3))
        elements.append(f'<polygon points="{base_x},{y_bottom} {base_x+5},{y_bottom-3} {base_x+5},{y_bottom+3}" fill="red"/>')
        elements.append(f'<polygon points="{base_x+width},{y_bottom} {base_x+width-5},{y_bottom-3} {base_x+width-5},{y_bottom+3}" fill="red"/>')
        elements.append(text(base_x + width/2, y_bottom + 10*scale + 7, f"{int(box['width'])} mm", 90*scale))

        # --- Left measurement line ---
        x_left = base_x - 2*side
        elements.append(line(x_left, base_y, x_left, base_y + length))
        elements.append(line(x_left - 3, base_y, x_left + 3, base_y))
        elements.append(line(x_left - 3, base_y + length, x_left + 3, base_y + length))
        elements.append(f'<polygon points="{x_left},{base_y} {x_left-3},{base_y+5} {x_left+3},{base_y+5}" fill="red"/>')
        elements.append(f'<polygon points="{x_left},{base_y+length} {x_left-3},{base_y+length-5} {x_left+3},{base_y+length-5}" fill="red"/>')
        elements.append(text(x_left - 10*scale, base_y + length/2, f"{int(box['length'])} mm", 90*scale, rotate=270))

        max_row_height = max(max_row_height, net_h)

        # --- Update offsets for next box ---
        if (i + 1) % columns == 0:
            row_widths.append(x_offset + net_w)
            x_offset = left_margin
            y_offset += max_row_height + spacing*scale
            max_row_height = 0
        else:
            x_offset += net_w + spacing*scale

    if len(boxes) % columns != 0:
        row_widths.append(x_offset - spacing*scale if x_offset > 0 else x_offset)

    canvas_width = max(row_widths) if row_widths else 500*scale
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
            r"E:\Program Files\Inkscape\bin\inkscape.exe",
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

# --- Add new box form (compact version) ---
with st.form("Add Box"):
    # Use 4 columns for Width, Length, Side, Label
    col_w, col_l, col_s, col_lab = st.columns(4)
    with col_w:
        width = st.number_input("Width (mm)", 100.0, 5000.0, 1442.0)
    with col_l:
        length = st.number_input("Length (mm)", 100.0, 5000.0, 2488.0)
    with col_s:
        side = st.number_input("Side / Tab size (mm)", 10.0, 500.0, 100.0)
    with col_lab:
        label_input = st.text_input("Label")

    # Use 4 columns for the direction selectors
    col_up, col_down, col_left, col_right = st.columns(4)
    option_values = ["None", "S", "SS", "L", "H"]
    with col_up:
        up_val = st.selectbox("Up", option_values)
    with col_down:
        down_val = st.selectbox("Down", option_values)
    with col_left:
        left_val = st.selectbox("Left", option_values)
    with col_right:
        right_val = st.selectbox("Right", option_values)

    submitted = st.form_submit_button("➕ Add Box")
    if submitted:
        st.session_state.boxes.append({
            "width": width,
            "length": length,
            "side": side,
            "label": label_input,
            "up": up_val,
            "down": down_val,
            "left": left_val,
            "right": right_val
        })

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
            r"E:\Program Files\Inkscape\bin\inkscape.exe",
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