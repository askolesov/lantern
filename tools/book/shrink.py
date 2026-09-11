from PIL import Image; import glob,os
for f in glob.glob("*/img/*.png"):
    j=f[:-4]+".jpg"
    if not os.path.exists(j) or os.path.getmtime(f)>os.path.getmtime(j):
        Image.open(f).convert("RGB").resize((1152,768),Image.LANCZOS).save(j,quality=85,optimize=True)
print(len(glob.glob("*/img/*.jpg")),"jpgs")
