# check_p1.py
"""Quick check if P1 imports work"""

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

print("=" * 60)
print("CHECKING P1 SETUP")
print("=" * 60)

# Test 1: Check imports
print("\n1. Testing imports...")
try:
    from src.utils import io
    print("   ✓ src.utils.io")
except Exception as e:
    print(f"   ✗ src.utils.io: {e}")

try:
    from src.utils import schema
    print("   ✓ src.utils.schema")
except Exception as e:
    print(f"   ✗ src.utils.schema: {e}")

try:
    from src.pipeline import normalize
    print("   ✓ src.pipeline.normalize")
except Exception as e:
    print(f"   ✗ src.pipeline.normalize: {e}")

try:
    from src.pipeline import ingest
    print("   ✓ src.pipeline.ingest")
except Exception as e:
    print(f"   ✗ src.pipeline.ingest: {e}")

try:
    from src.pipeline import router
    print("   ✓ src.pipeline.router")
except Exception as e:
    print(f"   ✗ src.pipeline.router: {e}")

try:
    from src.pipeline import agent
    print("   ✓ src.pipeline.agent")
except Exception as e:
    print(f"   ✗ src.pipeline.agent: {e}")

# Test 2: Check if __init__.py files exist
print("\n2. Checking __init__.py files...")
init_files = [
    "src/__init__.py",
    "src/pipeline/__init__.py",
    "src/utils/__init__.py",
    "src/models/__init__.py",
    "src/integration/__init__.py",
]

for init_file in init_files:
    path = ROOT / init_file
    exists = path.exists()
    status = "✓" if exists else "✗ MISSING"
    print(f"   {status} {init_file}")

# Test 3: Check data files
print("\n3. Checking data files...")
data_files = [
    "data/paper.txt",
    "data/answer_key.csv",
]

for data_file in data_files:
    path = ROOT / data_file
    exists = path.exists()
    size = f"({path.stat().st_size} bytes)" if exists else ""
    status = "✓" if exists else "✗ MISSING"
    print(f"   {status} {data_file} {size}")

# Test 4: Try basic P1 functionality
print("\n4. Testing P1 basic functionality...")
try:
    from src.pipeline.ingest import DocumentParser
    parser = DocumentParser()
    print("   ✓ Can create DocumentParser")
    
    # Test with sample text
    sample = """Q1. Find x in 2x + 5 = 13
(1) x = 3
(2) x = 4
(3) x = 5
(4) x = 6"""
    
    qtexts, options = parser._extract_questions_and_options(sample)
    print(f"   ✓ Parser works: found {len(qtexts)} questions")
    
    if len(qtexts) > 0:
        print(f"   ✓ Question extracted: {list(qtexts.keys())[0]}")
        print(f"   ✓ Options extracted: {len(list(options.values())[0])} options")
    
except Exception as e:
    print(f"   ✗ P1 functionality test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("CHECK COMPLETE")
print("=" * 60)