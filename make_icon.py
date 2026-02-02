from PIL import Image
import os

png_path = r"C:/Users/EL7md/.gemini/antigravity/brain/3097e0ce-0d08-415e-84f1-27b3da8fa7ad/academy_logo_icon_1770038574191.png"
ico_path = os.path.join(os.getcwd(), "app_icon.ico")

img = Image.open(png_path)
# Resize to common icon sizes
icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save(ico_path, sizes=icon_sizes)
print(f"Icon saved at: {ico_path}")
