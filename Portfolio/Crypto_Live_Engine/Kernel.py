from apscheduler.schedulers.blocking import BlockingScheduler
from BinanceBot.Tasks import ga_optimisor, screener
import logging
from apscheduler.events import EVENT_JOB_ERROR

scheduler = BlockingScheduler()
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

# Run screener at the start of every 15th minute (e.g., :15, :30, :45, :00)
scheduler.add_job(
    screener.run_screener(),
    trigger='cron',
    minute='15'
)

# Run ga_optimisor every 3 days at midnight
scheduler.add_job(
    ga_optimisor.ga_optimise,
    trigger='cron',
    hour=0,
    minute=0,
    day='*/3'
)

def job_error_listener(event):
    if event.exception:
        print(f"Job crashed: {event.job_id}")
    else:
        print(f"Job completed successfully: {event.job_id}")

scheduler.add_listener(job_error_listener, EVENT_JOB_ERROR)

def main():
    scheduler.start()

if __name__ == "__main__":
    main()
