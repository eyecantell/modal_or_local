# Run each of the tests using 'modal run testname.py'
# PRW todo - create a pytest plugin to handle this? would have to work around pytest ignoring decorated functions
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor


def run_test(file):
    command = f"modal run {file}"
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()

    print(f"'{file}': {'successful' if process.returncode==0 else 'failed'}")
    if process.returncode != 0:
        print(stderr.decode())
        print(f"To run this test individually try 'modal run {file}'\n--\n")
    return {
        "file": file,
        "returncode": process.returncode,
        "stderr": stderr.decode(),
        "stdout": stdout.decode(),
    }


tests_dir = os.path.dirname(os.path.abspath(__file__))
test_file_full_paths = [
    f"{tests_dir}/{file}"
    for file in os.listdir(tests_dir)
    if file.startswith("test_") and file.endswith(".py")
]
print(f"{test_file_full_paths=}")
with ThreadPoolExecutor() as executor:
    results = list(executor.map(run_test, test_file_full_paths))

success_count = 0
fail_count = 0
for r in results:
    if r.get("returncode") == 0:
        success_count += 1
    else:
        fail_count += 1
print(f"{success_count=}, {fail_count=}")

assert fail_count < 1, f"{fail_count} tests failed"
