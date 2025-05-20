import dateparser
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from tool_decorator import tool
from tools.execute_shell_command import execute_shell_command

scheduler = BackgroundScheduler()
scheduler.start()

scheduled_jobs = []

@tool("Schedules a shell command to run at a specific time using natural language (e.g. 'in 10 minutes', 'tomorrow at 8AM')")
def schedule_task(command:str, run_at:str):
    run_time = dateparser.parse(run_at)
    if not run_time:
        return f"Could not parse time string: '{run_at}'"

    def task():
        print(f"[Scheduled Task] Running: {command}")
        print(execute_shell_command(command))
        print("> ")

    job = scheduler.add_job(task, trigger='date', run_date=run_time)
    scheduled_jobs.append({
        "id": job.id,
        "command": command,
        "run_at": run_time.isoformat()
    })

    return f"Task scheduled to run at {run_time}."