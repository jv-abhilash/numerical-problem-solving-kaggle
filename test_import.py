# test_imports.py
print("Testing imports...")

try:
    import pymupdf
    print("✓ PyMuPDF imported successfully")
    print(f"  Version: {pymupdf.version}")
except ImportError as e:
    print(f"✗ PyMuPDF import failed: {e}")

try:
    import pdfplumber
    print("✓ pdfplumber imported successfully")
except ImportError as e:
    print(f"✗ pdfplumber import failed: {e}")

try:
    from src.pipeline.ingest import DocumentParser
    print("✓ DocumentParser imported successfully")
    parser = DocumentParser()
    print("✓ DocumentParser instance created")
except Exception as e:
    print(f"✗ DocumentParser import/creation failed: {e}")