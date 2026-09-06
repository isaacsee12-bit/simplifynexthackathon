import os
import sys
sys.path.insert(0, os.path.abspath('.'))
from analyzers.image_analyzer import image_analyzer

print("Testing image analyzer...")
try:
    with open('tests/verification_files/test_img_0.jpg', 'rb') as f:
        res, ctx = image_analyzer.analyze(f.read(), 'test_img_0.jpg')
        print(res)
        print(ctx)
except Exception as e:
    print(f"Error: {e}")
