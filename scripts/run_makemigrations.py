import subprocess
import sys

proc = subprocess.Popen(
    [sys.executable, 'manage.py', 'makemigrations', 'tenants'],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
)

for char in iter(lambda: proc.stdout.read(1), ''):
    sys.stdout.write(char)
    sys.stdout.flush()
    if char == ']': # Assuming prompt ends with [y/N]
        proc.stdin.write('y\n')
        proc.stdin.flush()

proc.wait()
print("\nDone")
