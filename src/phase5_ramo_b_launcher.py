"""
Wrapper per phase5_ramo_b.py su Windows con torch nightly (RTX 5060 Ti).
Forza il caricamento delle DLL CUDA prima dell'import torch.
"""
import os, sys, ctypes
from pathlib import Path

# Step 1: variabili ambiente
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["CUDA_MODULE_LOADING"] = "LAZY"

# Step 2: trova e pre-carica le DLL dipendenti di shm.dll
torch_lib = Path(sys.executable).parent / "Lib" / "site-packages" / "torch" / "lib"
if not torch_lib.exists():
    # Cerca in sys.path
    for p in sys.path:
        candidate = Path(p) / "torch" / "lib"
        if candidate.exists():
            torch_lib = candidate
            break

print(f"torch lib dir: {torch_lib}")

# Pre-carica DLL in ordine (shm.dll dipende da queste)
dll_order = [
    "asmjit.dll",
    "fbgemm.dll", 
    "libiomp5md.dll",
    "uv.dll",
    "c10.dll",
    "c10_cuda.dll",
    "torch_cpu.dll",
    "torch_cuda.dll",
    "torch.dll",
    "shm.dll",
]

loaded = []
for dll_name in dll_order:
    dll_path = torch_lib / dll_name
    if dll_path.exists():
        try:
            ctypes.CDLL(str(dll_path))
            loaded.append(dll_name)
        except OSError as e:
            pass  # Alcuni non sono necessari

print(f"DLL pre-caricate: {loaded}")

# Step 3: aggiungi torch lib al PATH di sistema
os.environ["PATH"] = str(torch_lib) + os.pathsep + os.environ.get("PATH", "")

# Step 4: ora importa torch
import torch
print(f"torch {torch.__version__} importato OK")
print(f"CUDA disponibile: {torch.cuda.is_available()}")

# Step 5: esegui il modulo principale con gli stessi argomenti
# sys.argv gia' corretto: launcher.py arg1 arg2 -> phase5_ramo_b.py vede arg1 arg2
sys.argv[0] = 'src/phase5_ramo_b.py'
exec(open("src/phase5_ramo_b.py").read())
