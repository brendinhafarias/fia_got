"""
zip_fia_got.py
Roda no console do PythonAnywhere.
Zipa toda a pasta /home/cfabrasil/fia_got em um único arquivo .zip
com timestamp no nome, salvo em /home/cfabrasil/
"""

import zipfile
import os
from pathlib import Path
from datetime import datetime

SOURCE_DIR = Path("/home/cfabrasil/fia_got")
TIMESTAMP  = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_ZIP = Path(f"/home/cfabrasil/fia_got_backup_{TIMESTAMP}.zip")

def zip_folder(source: Path, output: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {source}")

    total_files = 0
    total_size  = 0

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in source.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(source.parent)  # mantém 'fia_got/...' dentro do zip
                zf.write(file_path, arcname)
                total_files += 1
                total_size  += file_path.stat().st_size
                print(f"  + {arcname}")

    zip_size = output.stat().st_size
    print(f"\n✅ Concluído!")
    print(f"   Arquivos comprimidos : {total_files}")
    print(f"   Tamanho original     : {total_size / 1024 / 1024:.2f} MB")
    print(f"   Tamanho do .zip      : {zip_size  / 1024 / 1024:.2f} MB")
    print(f"   Salvo em             : {output}")

if __name__ == "__main__":
    print(f"Zipando '{SOURCE_DIR}' → '{OUTPUT_ZIP}' …\n")
    zip_folder(SOURCE_DIR, OUTPUT_ZIP)
