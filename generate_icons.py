import os
from PIL import Image, ImageDraw, ImageFont

def create_icon(size, path):
    img = Image.new('RGB', (size, size), color = (10, 14, 39))
    d = ImageDraw.Draw(img)
    # Draw a simple magnifying glass or letter T
    d.text((size/4, size/4), "T", fill=(0, 212, 255))
    img.save(path)

os.makedirs('extension/icons', exist_ok=True)
create_icon(16, 'extension/icons/icon16.png')
create_icon(48, 'extension/icons/icon48.png')
create_icon(128, 'extension/icons/icon128.png')
print("Icons created")
