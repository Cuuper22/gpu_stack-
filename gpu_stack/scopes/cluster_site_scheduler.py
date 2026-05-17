"""
Scheduler and provisioning overhead for site-level jobs.
"""

from ..core.units import SECOND
from .cluster_site_common import scheduler_overhead_eq, scheduler_overhead_var


scheduler_queue_wait = scheduler_overhead_var(
    "cluster.sched.queue_wait", "T_queue", "s",
    "Time a job spends waiting in the scheduler queue.",
    sp_units=SECOND,
)
scheduler_allocation_time = scheduler_overhead_var(
    "cluster.sched.allocation_time", "T_alloc", "s",
    "Control-plane time to allocate nodes, wire up containers, and stage the job.",
    sp_units=SECOND,
)
provisioning_time = scheduler_overhead_var(
    "cluster.sched.provisioning_time", "T_prov", "s",
    "Time spent on image pull, filesystem mounts, and runtime startup.",
    sp_units=SECOND,
)
job_start_delay = scheduler_overhead_var(
    "cluster.sched.job_start_delay", "T_start_delay", "s",
    "End-to-end delay between job submission and first training step.",
    sp_units=SECOND,
)


eq_job_start_delay = scheduler_overhead_eq(
    "cluster.eq.job_start_delay",
    job_start_delay.symbol,
    scheduler_queue_wait.symbol + scheduler_allocation_time.symbol + provisioning_time.symbol,
    "Job start delay equals queue wait plus scheduler allocation plus provisioning time.",
    check_units=True,
)


CLUSTER_SITE_SCHEDULER_VARIABLES = [
    scheduler_queue_wait,
    scheduler_allocation_time,
    provisioning_time,
    job_start_delay,
]

CLUSTER_SITE_SCHEDULER_EQUATIONS = [
    eq_job_start_delay,
]


__all__ = [
    "scheduler_queue_wait", "scheduler_allocation_time", "provisioning_time",
    "job_start_delay",
    "eq_job_start_delay",
]
