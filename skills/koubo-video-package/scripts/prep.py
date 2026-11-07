"""Write data.js from the rough-cut folder."""
import csv, json, os, sys
build, assets, out = sys.argv[1:4]
frames = len([f for f in os.listdir(f"{build}/frames") if f.startswith("f_")])
step = 6
pts = [None] * (frames // step + 2)
for row in csv.reader(open(f"{build}/face.csv")):
    pts[int(row[0]) // step] = [float(row[1]), float(row[2])]
data = dict(edl=json.load(open(f"{build}/edl.json")), face=dict(step=step, pts=pts), frames=frames, fps=30,
            assets=assets, framesDir=f"{build}/frames", cutDir=f"{build}/cut",
            beat=json.load(open(f"{build}/beat.json")) if os.path.exists(f"{build}/beat.json") else None)
open(out, "w").write("const DATA=" + json.dumps(data) + ";")
print("frames", frames)
