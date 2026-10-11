"""Rasterize the existing code-defined favicon geometry for Windows icon sizes."""
from pathlib import Path
from PIL import Image, ImageDraw

root=Path(__file__).resolve().parents[1]
image=Image.new('RGBA',(256,256),(0,0,0,0))
draw=ImageDraw.Draw(image)
draw.rounded_rectangle((0,0,255,255),radius=77,fill='#06145c')
draw.polygon([(160,64),(134,147),(64,192),(96,102)],fill='#bdd3ff')
image.save(root/'packaging/windows/app.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
