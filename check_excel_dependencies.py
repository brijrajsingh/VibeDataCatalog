"""
Verify that all dependencies for Excel file preview are properly installed
"""
import importlib
import sys

def check_dependencies():
    """Check if all required packages are installed and properly working"""
    required_packages = {
        'pandas': 'For data manipulation and Excel reading',
        'openpyxl': 'For reading .xlsx files',
        'xlrd': 'For reading .xls files',
        'numpy': 'For numerical operations'
    }
    
    missing = []
    issues = []
    
    print("Verifying Excel preview dependencies...")
    print("-" * 50)
    
    for package, description in required_packages.items():
        print(f"Checking {package}... ", end="")
        try:
            module = importlib.import_module(package)
            version = getattr(module, '__version__', 'unknown version')
            print(f"OK (v{version})")
        except ImportError:
            print("MISSING")
            missing.append(package)
        except Exception as e:
            print(f"ERROR: {str(e)}")
            issues.append((package, str(e)))
    
    print("-" * 50)
    
    if not missing and not issues:
        print("✓ All dependencies are properly installed!")
        
        # Additional pandas test
        print("\nTesting pandas Excel reading capability...")
        import pandas as pd
        import io
        
        # Create a simple in-memory Excel file
        output = io.BytesIO()
        df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        
        try:
            # Write to Excel
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            # Reset pointer and read back
            output.seek(0)
            df_read = pd.read_excel(output, engine='openpyxl')
            
            print("✓ Successfully created and read an Excel file with pandas!")
            print(f"✓ DataFrame content: \n{df_read}")
            return True
        except Exception as e:
            print(f"✗ Error in pandas Excel test: {str(e)}")
            return False
    else:
        if missing:
            print("✗ Missing packages:")
            for package in missing:
                print(f"  - {package}: {required_packages[package]}")
            print("\nPlease install the missing packages with:")
            print(f"pip install {' '.join(missing)}")
            
        if issues:
            print("\n✗ Packages with issues:")
            for package, error in issues:
                print(f"  - {package}: {error}")
                
        return False

if __name__ == "__main__":
    success = check_dependencies()
    sys.exit(0 if success else 1)
