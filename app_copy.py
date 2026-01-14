import streamlit as st
import tempfile
from pathlib import Path
import cairosvg

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
        line_end_y = center_y - arrow_length + arrow_head_size
        elements.append(f'<line x1="{center_x}" y1="{center_y}" x2="{center_x}" y2="{line_end_y}" stroke="red" stroke-width="1"/>')
        elements.append(f'<polygon points="{center_x},{line_end_y - arrow_head_size} {center_x - arrow_head_size},{line_end_y} {center_x + arrow_head_size},{line_end_y}" fill="red"/>')

        # --- Inputs inside the box ---
        if box.get("up") and box["up"] != "None":
            elements.append(text(base_x + width/2, base_y + length*0.25, box["up"], 50*scale, "red"))
        if box.get("down") and box["down"] != "None":
            elements.append(text(base_x + width/2, base_y + length*0.75, box["down"], 50*scale, "red"))
        if box.get("left") and box["left"] != "None":
            elements.append(text(base_x + width*0.25, base_y + length/2, box["left"], 50*scale, "red"))
        if box.get("right") and box["right"] != "None":
            elements.append(text(base_x + width*0.75, base_y + length/2, box["right"], 50*scale, "red"))

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

# ---------- STREAMLIT UI ----------
st.set_page_config(layout="wide")
st.title("📦 Box Net Creator - Web Version")

if "boxes" not in st.session_state:
    st.session_state.boxes = []

# --- Add new box form ---
with st.form("Add Box"):
    col_w, col_l, col_s, col_lab = st.columns(4)
    with col_w: width = st.number_input("Width (mm)", 100.0, 5000.0, 1442.0)
    with col_l: length = st.number_input("Length (mm)", 100.0, 5000.0, 2488.0)
    with col_s: side = st.number_input("Side / Tab size (mm)", 10.0, 500.0, 100.0)
    with col_lab: label_input = st.text_input("Label")

    col_up, col_down, col_left, col_right = st.columns(4)
    option_values = ["None", "S", "SS", "L", "H"]
    with col_up: up_val = st.selectbox("Up", option_values)
    with col_down: down_val = st.selectbox("Down", option_values)
    with col_left: left_val = st.selectbox("Left", option_values)
    with col_right: right_val = st.selectbox("Right", option_values)

    submitted = st.form_submit_button("➕ Add Box")
    if submitted:
        st.session_state.boxes.append({
            "width": width, "length": length, "side": side,
            "label": label_input, "up": up_val, "down": down_val,
            "left": left_val, "right": right_val
        })

# --- Show added boxes ---
st.subheader("Boxes Added")
for i, box in enumerate(st.session_state.boxes):
    st.write(f"{i+1}. {box['label']} - {box['width']}x{box['length']} mm, Side: {box['side']} mm, Up:{box['up']} Down:{box['down']} Left:{box['left']} Right:{box['right']}")

# --- Clear all boxes ---
if st.button("🗑️ Clear All Boxes"):
    st.session_state.boxes = []

# --- Generate SVG + PDF ---
if st.session_state.boxes:
    svg_code = generate_box_sheet_svg(st.session_state.boxes)

    # Preview PNG using CairoSVG
    with tempfile.TemporaryDirectory() as tmp:
        png_path = Path(tmp) / "box_sheet.png"
        pdf_path = Path(tmp) / "box_sheet.pdf"

        cairosvg.svg2png(bytestring=svg_code.encode("utf-8"), write_to=str(png_path))
        st.subheader("Preview")
        st.image(str(png_path))

        # Download PDF
        cairosvg.svg2pdf(bytestring=svg_code.encode("utf-8"), write_to=str(pdf_path))
        st.download_button(
            "⬇️ Download PDF",
            data=pdf_path.read_bytes(),
            file_name="box_sheet.pdf",
            mime="application/pdf"
        )
