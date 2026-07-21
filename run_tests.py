# -*- coding: utf-8 -*-
"""运行测试并显示详细结果"""
import subprocess
import sys

test_files = [
    "tests/test_config_manager.py",
    "tests/test_exceptions.py",
    "tests/test_pipeline.py",
    "tests/test_lut_filters.py",
    "tests/test_app_data_paths.py",
]

results = []
for test_file in test_files:
    print(f"\n{'='*60}")
    print(f"Running: {test_file}")
    print('='*60)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
        capture_output=True,
        text=True,
        cwd="e:/Projects/app"
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    results.append((test_file, result.returncode))

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
for test_file, returncode in results:
    status = "✓ PASSED" if returncode == 0 else "✗ FAILED"
    print(f"{status}: {test_file}")
