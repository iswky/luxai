import os
import time
import subprocess
import sys

def run_parser():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting parser...")
    try:
        # run main.py as a subprocess
        env = os.environ.copy()
        env["INTERACTIVE_MODE"] = "false"
        subprocess.run([sys.executable, "parser/main.py"], check=True, env=env)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Parser finished successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Parser failed with exit code {e.returncode}")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] An error occurred: {e}")

def main():
    interval = int(os.getenv("PARSER_INTERVAL_SECONDS", "3600"))
    print(f"Scheduler started. Interval: {interval} seconds.")

    while True:
        run_parser()
        print(f"Waiting {interval} seconds for the next run...")
        time.sleep(interval)

if __name__ == "__main__":
    main()
