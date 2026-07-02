import os, sys, ctypes
from pathlib import Path

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
torch_lib = None
for p in sys.path:
    c = Path(p) / "torch" / "lib"
    if c.exists():
        torch_lib = c
        break
if torch_lib:
    for dll in ["c10.dll","c10_cuda.dll","torch_cpu.dll","torch_cuda.dll","torch.dll","shm.dll"]:
        p = torch_lib / dll
        if p.exists():
            try: ctypes.CDLL(str(p))
            except: pass
    os.environ["PATH"] = str(torch_lib) + os.pathsep + os.environ.get("PATH","")

import torch
ckpt = torch.load(r"results/checkpoints/phase3_gnn_best.pt",
                  map_location="cpu", weights_only=False)

if isinstance(ckpt, dict):
    print("Keys del dict:", list(ckpt.keys()))
    if "model_state_dict" in ckpt:
        sd = ckpt["model_state_dict"]
    elif "state_dict" in ckpt:
        sd = ckpt["state_dict"]
    else:
        sd = ckpt
else:
    sd = ckpt

print("\nLayer names nel checkpoint:")
for k, v in sd.items():
    print(f"  {k}: {v.shape}")
