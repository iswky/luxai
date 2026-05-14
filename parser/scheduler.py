import os
import time
import subprocess
import sys
from dotenv import load_dotenv

# path to .env file in the root directory (mapped via docker volume)
ENV_PATH = "/app/.env"

# description: function run_parser. args: . returns: any.
def run_parser():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting parser...")
    try:
        env = os.environ.copy()
        env["INTERACTIVE_MODE"] = "false"
        # pass the absolute path to main.py
        subprocess.run([sys.executable, "/app/parser/main.py"], check=True, env=env)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Parser finished successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Parser failed with exit code {e.returncode}")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] An error occurred: {e}")

# description: function get_interval. args: . returns: any.
def get_interval():
    # reload .env from disk
    if os.path.exists(ENV_PATH):
        load_dotenv(ENV_PATH, override=True)
    return int(os.getenv("PARSER_INTERVAL_SECONDS", "3600"))

# description: function main. args: . returns: any.
def main():
    current_interval = get_interval()
    print(f"Scheduler started. Initial interval: {current_interval} seconds.")

    while True:
        # run the parser
        run_parser()

        # wait for the next run, but check for interval changes every 10 seconds
        start_wait = time.time()
        while True:
            elapsed = time.time() - start_wait
            if elapsed >= current_interval:
                break

            # check for changes in .env
            new_interval = get_interval()
            if new_interval != current_interval:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Interval changed from {current_interval} to {new_interval}. Restarting cycle...")
                current_interval = new_interval
                # break internal loop to run parser immediately and reset cycle
                break

            time.sleep(10) # check for changes every 10 seconds

if __name__ == "__main__":
    main()
