#!/usr/bin/env python3
"""
UI Dump Visualization Tool

This script reads JSON UI dump files and corresponding TGA screenshots,
then overlays the UI element bounding boxes and labels on the images
to verify that the UI instrumentation is working correctly.

Usage: python3 visualize_ui_dump.py [input_dir] [output_dir]
"""

import json
import os
import sys
import struct
from PIL import Image, ImageDraw, ImageFont
import argparse

def read_tga(filepath):
    """Read a TGA file and return PIL Image"""
    with open(filepath, 'rb') as f:
        # Read TGA header (18 bytes)
        header = f.read(18)
        
        # Parse header
        id_length = header[0]
        color_map_type = header[1]
        image_type = header[2]
        
        # Skip color map info (5 bytes)
        
        # Image specification
        x_origin = struct.unpack('<H', header[8:10])[0]
        y_origin = struct.unpack('<H', header[10:12])[0]
        width = struct.unpack('<H', header[12:14])[0]
        height = struct.unpack('<H', header[14:16])[0]
        pixel_depth = header[16]
        image_descriptor = header[17]
        
        # Skip image ID if present
        if id_length > 0:
            f.read(id_length)
        
        # Read pixel data
        bytes_per_pixel = pixel_depth // 8
        pixel_data = f.read(width * height * bytes_per_pixel)
        
        if bytes_per_pixel == 4:  # RGBA
            # Convert BGRA to RGBA (TGA stores in BGRA order)
            rgba_data = bytearray()
            for i in range(0, len(pixel_data), 4):
                b, g, r, a = pixel_data[i:i+4]
                rgba_data.extend([r, g, b, a])
            
            img = Image.frombytes('RGBA', (width, height), bytes(rgba_data))
        elif bytes_per_pixel == 3:  # RGB
            # Convert BGR to RGB
            rgb_data = bytearray()
            for i in range(0, len(pixel_data), 3):
                b, g, r = pixel_data[i:i+3]
                rgb_data.extend([r, g, b])
            
            img = Image.frombytes('RGB', (width, height), bytes(rgb_data))
        else:
            raise ValueError(f"Unsupported pixel depth: {pixel_depth}")
        
        # Check if image origin is bottom-left (bit 5 of image_descriptor)
        if not (image_descriptor & 0x20):
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
        
        return img

def get_color_for_type(ui_type):
    """Return color based on UI element type"""
    colors = {
        'window': '#FF0000',      # Red
        'button': '#00FF00',      # Green
        'header': '#0000FF',      # Blue
        'tabitem': '#FF00FF',     # Magenta
        'child': '#FFFF00',       # Yellow
        'item': '#00FFFF',        # Cyan
        'slider': '#FFA500',      # Orange
        'checkbox': '#800080',    # Purple
        'text': '#808080',        # Gray
    }
    return colors.get(ui_type, '#FFFFFF')  # White for unknown types

def visualize_ui_dump(json_path, tga_path, output_path):
    """Overlay UI elements from JSON onto TGA image"""
    
    # Load JSON data
    with open(json_path, 'r') as f:
        ui_data = json.load(f)
    
    # Load TGA image
    try:
        img = read_tga(tga_path)
    except Exception as e:
        print(f"Error reading TGA {tga_path}: {e}")
        return False
    
    # Convert to RGBA if not already
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Create drawing context
    draw = ImageDraw.Draw(img)
    
    # Try to load a font, fallback to default if not available
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except:
        font = ImageFont.load_default()
        font_small = font
    
    # Draw each UI element
    for node in ui_data.get('nodes', []):
        bbox = node.get('bbox', [0, 0, 0, 0])
        x, y, w, h = bbox
        
        # Skip elements with invalid dimensions
        if w <= 0 or h <= 0:
            continue
        
        ui_type = node.get('type', 'unknown')
        label = node.get('label', '')
        visible = node.get('visible', True)
        hovered = node.get('hovered', False)
        active = node.get('active', False)
        
        # Choose color and line style based on element properties
        color = get_color_for_type(ui_type)
        
        if not visible:
            color = '#808080'  # Gray for invisible elements
        elif active:
            color = '#FF0000'  # Red for active elements
        elif hovered:
            color = '#FFAA00'  # Orange for hovered elements
        
        # Draw bounding box
        line_width = 2 if active else 1
        draw.rectangle([x, y, x + w, y + h], outline=color, width=line_width)
        
        # Draw label if there's space
        if len(label) > 0 and w > 30 and h > 15:
            # Truncate long labels
            display_label = label[:20] + "..." if len(label) > 20 else label
            
            # Calculate text position (try to fit inside the element)
            text_bbox = draw.textbbox((0, 0), display_label, font=font_small)
            text_w = text_bbox[2] - text_bbox[0]
            text_h = text_bbox[3] - text_bbox[1]
            
            text_x = x + 2
            text_y = y + 2
            
            # If text doesn't fit inside, put it above the element
            if text_w > w - 4 or text_h > h - 4:
                text_y = max(0, y - text_h - 2)
            
            # Draw text background
            draw.rectangle([text_x - 1, text_y - 1, text_x + text_w + 1, text_y + text_h + 1], 
                          fill='#000000AA')
            
            # Draw text
            draw.text((text_x, text_y), display_label, fill=color, font=font_small)
        
        # Draw type indicator in corner
        type_text = ui_type[:3].upper()
        type_bbox = draw.textbbox((0, 0), type_text, font=font_small)
        type_w = type_bbox[2] - type_bbox[0]
        type_h = type_bbox[3] - type_bbox[1]
        
        type_x = x + w - type_w - 2
        type_y = y + h - type_h - 2
        
        if type_x >= x and type_y >= y:
            draw.rectangle([type_x - 1, type_y - 1, type_x + type_w + 1, type_y + type_h + 1], 
                          fill='#000000AA')
            draw.text((type_x, type_y), type_text, fill=color, font=font_small)
    
    # Add legend
    legend_y = 10
    legend_x = 10
    draw.rectangle([legend_x - 5, legend_y - 5, legend_x + 200, legend_y + 120], 
                  fill='#000000CC', outline='#FFFFFF')
    
    legend_items = [
        ('Window', '#FF0000'),
        ('Button', '#00FF00'),
        ('Header', '#0000FF'),
        ('Tab', '#FF00FF'),
        ('Child', '#FFFF00'),
        ('Item', '#00FFFF'),
        ('Active', '#FF0000'),
        ('Hovered', '#FFAA00'),
        ('Hidden', '#808080'),
    ]
    
    for i, (name, color) in enumerate(legend_items):
        y_pos = legend_y + i * 12
        draw.rectangle([legend_x, y_pos, legend_x + 10, y_pos + 10], fill=color)
        draw.text((legend_x + 15, y_pos), name, fill='#FFFFFF', font=font_small)
    
    # Add frame info
    frame_info = f"Frame: {ui_data.get('frame', 'N/A')}, Elements: {len(ui_data.get('nodes', []))}"
    draw.text((10, img.height - 25), frame_info, fill='#FFFFFF', font=font)
    
    # Save the result
    img.save(output_path, 'PNG')
    return True

def main():
    parser = argparse.ArgumentParser(description='Visualize UI dump data overlaid on screenshots')
    parser.add_argument('input_dir', nargs='?', default='/tmp/rs-viewer-ui', 
                       help='Directory containing UI dump files (default: /tmp/rs-viewer-ui)')
    parser.add_argument('output_dir', nargs='?', default='/tmp/ui-visualization',
                       help='Directory to save visualization images (default: /tmp/ui-visualization)')
    parser.add_argument('--latest', action='store_true',
                       help='Only process the latest file pair')
    parser.add_argument('--count', type=int, default=10,
                       help='Number of latest file pairs to process (default: 10)')
    parser.add_argument('--all', action='store_true',
                       help='Process all available file pairs')
    
    args = parser.parse_args()
    
    input_dir = args.input_dir
    output_dir = args.output_dir
    
    if not os.path.exists(input_dir):
        print(f"Error: Input directory {input_dir} does not exist")
        sys.exit(1)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Find JSON files
    json_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    json_files.sort()
    
    if not json_files:
        print(f"No JSON files found in {input_dir}")
        sys.exit(1)
    
    # Select which files to process
    if args.latest:
        json_files = [json_files[-1]]
    elif not args.all:
        # Process the last N files (default: 10)
        json_files = json_files[-args.count:]
    
    print(f"Processing {len(json_files)} files...")
    
    success_count = 0
    for json_file in json_files:
        base_name = json_file[:-5]  # Remove .json extension
        tga_file = base_name + '.tga'
        
        json_path = os.path.join(input_dir, json_file)
        tga_path = os.path.join(input_dir, tga_file)
        output_path = os.path.join(output_dir, base_name + '_visualized.png')
        
        if not os.path.exists(tga_path):
            print(f"Warning: TGA file {tga_file} not found, skipping {json_file}")
            continue
        
        try:
            if visualize_ui_dump(json_path, tga_path, output_path):
                print(f"✓ Created {output_path}")
                success_count += 1
            else:
                print(f"✗ Failed to process {json_file}")
        except Exception as e:
            print(f"✗ Error processing {json_file}: {e}")
    
    print(f"\nCompleted: {success_count}/{len(json_files)} files processed successfully")
    print(f"Output directory: {output_dir}")

if __name__ == '__main__':
    main()
