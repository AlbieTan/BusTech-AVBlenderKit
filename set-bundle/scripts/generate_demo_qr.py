"""Create a real, explicitly non-submission demo QR encoding https://example.com.

Run with the Codex bundled Python (reportlab installed). Replace this image
once the team's final link is available.
"""

from pathlib import Path
from reportlab.graphics.barcode import qr
from PIL import Image

here = Path(__file__).resolve().parent
widget = qr.QrCodeWidget('https://example.com')
widget.qr.make()
count = widget.qr.getModuleCount()
border = 4
scale = 12
image = Image.new('RGB', ((count + 2 * border) * scale,) * 2, 'white')
pixels = image.load()
for y in range(count):
    for x in range(count):
        if widget.qr.isDark(y, x):
            for yy in range((y + border) * scale, (y + border + 1) * scale):
                for xx in range((x + border) * scale, (x + border + 1) * scale):
                    pixels[xx, yy] = (0, 0, 0)
image.save(here / 'demo_qr_example_com.png')
print('DEMO_QR_CREATED: https://example.com')
