"""Run every play-test in turn. Needs: pip install playwright && playwright install chromium"""
import subprocess, sys
from pathlib import Path

here = Path(__file__).resolve().parent
failed = []
for test in sorted(here.glob('test_*.py')):
    print(f'\n=== {test.name}')
    out = subprocess.run([sys.executable, str(test)], cwd=here, capture_output=True, text=True)
    print(out.stdout[-2500:] + out.stderr[-1500:])
    if out.returncode or 'FAIL' in out.stdout or 'errors: [' in out.stdout and 'errors: []' not in out.stdout:
        failed.append(test.name)
print('\nAll play-tests passed.' if not failed else '\nNeeds a look: ' + ', '.join(failed))
sys.exit(1 if failed else 0)
