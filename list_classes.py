import ast
from pathlib import Path

def print_classes_in_folder(folder_path):
    path = Path(folder_path)
    
    # Locate all .py files in the folder (and its subfolders using rglob)
    py_files = list(path.rglob("*.py"))
    
    if not py_files:
        print(f"No Python files found in '{folder_path}'")
        return

    print(f"Searching for classes in: {path.resolve()}\n")
    
    for file_path in py_files:
        try:
            # Read the contents of the python file
            content = file_path.read_text(encoding="utf-8")
            
            # Parse the code into an Abstract Syntax Tree
            tree = ast.parse(content)
            
            # Filter and extract top-level class definitions
            classes = [node.name for node in ast.iter_child_nodes(tree) if isinstance(node, ast.ClassDef)]
            
            if classes:
                # Print the relative path of the file and its classes
                relative_path = file_path.relative_to(path)
                print(f"📄 {relative_path}")
                for class_name in classes:
                    print(f"   └── class {class_name}")
                print()
                
        except (SyntaxError, UnicodeDecodeError) as e:
            # Safely handle files that aren't valid Python or have decoding issues
            print(f"⚠️ Could not parse {file_path.name}: {e}\n")

# Example usage: Replace '.' with your target folder directory path
print_classes_in_folder('./modules')
