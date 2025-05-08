import nbformat
import sys
import os

def extract_model_class(nb_path, class_name, output_path="model.py"):
    nb = nbformat.read(nb_path, as_version=4)
    model_code = []

    for cell in nb.cells:
        if cell.cell_type == "code" and f"class {class_name}" in cell.source:
            model_code.append(cell.source)

    if not model_code:
        print(f"❌ Model class '{class_name}' not found in notebook.")
        return

    with open(output_path, "w") as f:
        f.write("import torch\nimport torch.nn as nn\n\n")
        f.write(model_code[0])
    print(f"✅ Model class '{class_name}' written to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_model.py <Notebook.ipynb> <ModelClassName>")
        sys.exit(1)

    ipynb_file, model_class = sys.argv[1:]
    extract_model_class(ipynb_file, model_class)
