# Roadmap

What is worth doing next. Nothing here is scheduled.

1. Fix a crash in the failure simulator. If a second failure lands after a replay
   but before the next checkpoint, recovery raises an error. The cause is in
   `WorkLedger.invalidate_outcomes` (`gpu_stack/research/recovery.py`) and
   `begin_recovery` (`gpu_stack/research/recovery_runtime.py`).

2. Fix a mislabeled field. `idle_subtracted_gpu_board_energy_j` currently holds the
   raw energy, not the energy with idle power taken out. Compute the real value or
   rename the field.

3. Decide what the collective-communication equations are for. Either use them when
   the calculator estimates training time, or label them clearly as a reference
   library that the time estimate does not use.

4. Fix the three economics presets that still look wrong. Facility overhead (PUE)
   never enters site power. The demand charge is counted twice. A 4-year life is
   applied to the whole facility instead of to the equipment it fits.

5. Measure energy on a real GPU with the cumulative energy counter. Sampled power
   readings are too coarse for the energy questions here.
