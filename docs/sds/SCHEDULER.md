# Scheduler Specification

The scheduler triggers recurring runtime jobs such as sensors and maintenance
tasks. The initial reference scheduler is deterministic and tick-driven: callers
provide the current time and explicitly ask the scheduler to run due jobs.

## Requirements
- Job registration emits `scheduler.job_registered`.
- Job removal emits `scheduler.job_unregistered`.
- Due jobs emit `scheduler.job_due`.
- Job execution emits `scheduler.job_started`.
- Successful jobs emit `scheduler.job_completed`.
- Failed jobs emit `scheduler.job_failed`.
- Scheduler timestamps must be timezone-aware.
- The scheduler must not perform AI reasoning.

## Job Model
- id: stable job identifier.
- interval_seconds: positive integer interval.
- handler: callable invoked when the job is due.

## Execution Model
The reference scheduler does not create a background thread. Runtime phases may
later add a managed loop that calls `run_due` on a configured cadence.

## Failure Behavior
When a job handler raises an exception, the scheduler emits
`scheduler.job_failed`, advances the next run time, and re-raises the exception
to the caller.
