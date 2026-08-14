# GPUSTACK observations

This directory holds machine-readable external measurements used to fit or
evaluate research models. An observation is evidence: a number someone
actually measured, with its source attached. It is not a scenario default.
Every record states what was measured, what was not reported, how uncertainty
was represented, and where the value came from.

`literature/e001-one-step-delay/` transcribes the Muon rows used to seed E001
from Tables 1 and 2 of [One-Step Gradient Delay is Not a Barrier for
Large-Scale Asynchronous Pipeline Parallel LLM
Pretraining](https://arxiv.org/html/2606.30634). The interval around each loss
is only the rounding interval implied by the paper's three-decimal table: the
uncertainty that comes from printing a number to three decimals, nothing more.
It is not a confidence interval or a substitute for repeated-run variance.

The E001 delay-response function is still a screening prior, a starting belief
used to narrow the search, not a fitted result. These observations do not
identify a mapping from final validation-loss delta to learning progress per
FLOP, and they cover one-step delay, one 360M model family, and Muon only.

The same three JSON records are bundled under
`gpu_stack/data/observations/literature/e001-one-step-delay/` as installed
package data. The command-line interface reads those packaged copies when no
`--observation` path is supplied, so default provenance still works from a
wheel or installed distribution. Keep the research copies here and the bundled
copies byte-for-byte identical; the fixture tests enforce that rule.
