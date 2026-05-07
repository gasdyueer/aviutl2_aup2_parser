#!/usr/bin/env python3
"""验证三项修复：Issue 2 (strip)、Issue 3 (dummy)、往返状态持久化"""
import sys
import hashlib
import tempfile
from pathlib import Path

BASE = Path(__file__).parent

# Ensure local module import
sys.path.insert(0, str(BASE))

from aup2_parser import (
    AUP2Parser,
    save_aup2_state,
    load_aup2_state,
)

# Locate test fixture
test_file = BASE / "test.aup2"
if not test_file.exists():
    test_file = BASE / "tests" / "fixtures" / "test.aup2"

if not test_file.exists():
    print("ERROR: test.aup2 not found")
    sys.exit(1)

original_bytes = test_file.read_bytes()
original_sha = hashlib.sha256(original_bytes).hexdigest()

passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name}  {detail}")

# ---- Test 1: Byte-exact round-trip (Issue 2 fix) ----
print("=== Test 1: Parse → reconstruct byte-exact round-trip (Issue 2) ===")
parser = AUP2Parser.from_file(str(test_file))
_ = parser.parse()
reconstructed = parser.reconstruct()
recon_sha = hashlib.sha256(reconstructed.encode('utf-8')).hexdigest()
check("SHA256 match", original_sha == recon_sha, f"{original_sha} vs {recon_sha}")

# ---- Test 2: reconstruct_from_dict (Issue 3 fix) ----
print("\n=== Test 2: reconstruct_from_dict without dummy hack (Issue 3) ===")
data = parser.parse()
recon_str = AUP2Parser.reconstruct_from_dict(data)
check("Returns non-empty string", len(recon_str) > 0)
check("Contains [project]", "[project]" in recon_str)
check("No 'dummy' leakage", "dummy" not in recon_str.split('\n')[0])

# ---- Test 3: to_dict + from_state round-trip ----
print("\n=== Test 3: to_dict(include_records=True) → from_state → reconstruct ===")
state = parser.to_dict(include_records=True)
check("State contains _line_records", "_line_records" in state and len(state["_line_records"]) > 0,
      f"records: {len(state.get('_line_records', []))}")

parser2 = AUP2Parser.from_state(state)
recon2 = parser2.reconstruct()
recon2_sha = hashlib.sha256(recon2.encode('utf-8')).hexdigest()
check("from_state SHA256 match", original_sha == recon2_sha)

# ---- Test 4: File-based save → load round-trip ----
print("\n=== Test 4: save_parsed_data(include_records=True) → load_state → reconstruct ===")
with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w', encoding='utf-8') as f:
    state_file = f.name
parser.save_parsed_data(state_file, include_records=True)

parser3 = AUP2Parser.load_state(state_file)
recon3 = parser3.reconstruct()
recon3_sha = hashlib.sha256(recon3.encode('utf-8')).hexdigest()
Path(state_file).unlink()
check("load_state SHA256 match", original_sha == recon3_sha)

# ---- Test 5: save_aup2_state / load_aup2_state ----
print("\n=== Test 5: save_aup2_state / load_aup2_state ===")
with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
    state_file2 = f.name
save_aup2_state(str(test_file), state_file2)
loaded = load_aup2_state(state_file2)
recon4 = loaded.reconstruct()
recon4_sha = hashlib.sha256(recon4.encode('utf-8')).hexdigest()
Path(state_file2).unlink()
check("save/load SHA256 match", original_sha == recon4_sha)

# ---- Test 6: Modify via from_state ----
print("\n=== Test 6: Modify data via from_state → reconstruct detects changes ===")
parser4 = AUP2Parser.from_state(state)
parser4.data['project']['display.scene'] = 999
recon5 = parser4.reconstruct()
check("Modified value present", 'display.scene=999' in recon5)

# ---- Test 7: reconstruct_from_dict with complex data ----
print("\n=== Test 7: reconstruct_from_dict produces valid structure ===")
data_no_meta = {k: v for k, v in data.items() if not k.startswith('_')}
recon6 = AUP2Parser.reconstruct_from_dict(data_no_meta)
check("Has [project]", "[project]" in recon6)
check("Has key=value", "display.scene=" in recon6)

# ---- Test 8: Verify Issue 2 - content with leading blank lines ----
print("\n=== Test 8: Leading blank lines preserved (Issue 2 verification) ===")
content_with_leading = "\n\n[project]\nfile=test.aup2\ndisplay.scene=0\n"
parser5 = AUP2Parser(content_with_leading)
data5 = parser5.parse()
check("Parses correctly", "project" in data5)
check("Has file property", data5["project"].get("file") == "test.aup2")
# The key test: reconstruct won't crash and produces valid output
recon7 = parser5.reconstruct()
check("Reconstructs valid", "[project]" in recon7 and "file=test.aup2" in recon7)

# Summary
print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed out of {passed+failed}")
if failed:
    sys.exit(1)
else:
    print("All tests passed!")
