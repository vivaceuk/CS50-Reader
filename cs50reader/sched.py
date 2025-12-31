#!/usr/bin/python
import os, logging
import schedule
import time
import subprocess
import signal
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

run_job = False

def job():
    subprocess.run(["python", "-m", "flask", "feed", "update"])


def cancel_scheduler(signum, frame):
    schedule.clear()
    global run_loop
    run_loop = False

signal.signal(signal.SIGINT, cancel_scheduler)
signal.signal(signal.SIGHUP, cancel_scheduler)
signal.signal(signal.SIGTERM, cancel_scheduler)

try:
    # Windows only...
    signal.signal(signal.CTRL_C_EVENT, cancel_scheduler)
except:
    pass

def main():
    parser = argparse.ArgumentParser(
                        prog='CS50Reader Scheduler',
                        description='',
                        epilog='')

    parser.add_argument('-i', '--interval', type=int, default=30, help='the frequency to poll feeds in minutes (default: %(default)s)')
    args = parser.parse_args()


    poll_interval = args.interval

    global run_loop
    run_loop = True

    schedule.every(poll_interval).minutes.do(job)

    logger.info(f" Polling for new articles every {poll_interval} minutes...")

    job()

    while run_loop:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    main()
