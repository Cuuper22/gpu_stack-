"""The `estimate` subcommand: the calculator from the command line."""

from __future__ import annotations

import argparse
import json
import sys

from gpu_stack import calculator


def add_estimate_parser(subparsers) -> None:
    p = subparsers.add_parser(
        "estimate",
        help="estimate training time, energy and cost for a model size, token count and GPU",
    )
    p.add_argument("--params", type=float, required=True, help="model size in parameters, e.g. 7e9")
    p.add_argument("--tokens", type=float, required=True, help="training tokens, e.g. 2e12")
    p.add_argument("--gpu", default="H100-SXM", help="GPU type: " + ", ".join(calculator.GPUS))
    p.add_argument("--gpus", type=float, default=1024, help="number of GPUs (default 1024)")
    p.add_argument("--mfu", type=float, help="share of peak speed reached (default 0.40; real runs 0.30-0.55)")
    p.add_argument("--pue", type=float, help="datacenter overhead (default 1.2)")
    p.add_argument("--electricity-price", type=float, dest="electricity_price", help="USD per kWh (default 0.0813)")
    p.add_argument("--gpu-price", type=float, dest="gpu_price", help="USD per GPU (default depends on the GPU)")
    p.add_argument("--life-years", type=float, dest="useful_life_years", help="years of use (default 4)")
    p.add_argument("--explain", action="store_true", help="print what each number is made of")
    p.add_argument("--json", action="store_true", help="print the results as JSON")
    p.set_defaults(func=cmd_estimate)


def cmd_estimate(args: argparse.Namespace) -> int:
    try:
        est = calculator.estimate(
            args.params, args.tokens, gpu=args.gpu, n_gpus=args.gpus, mfu=args.mfu, pue=args.pue,
            electricity_price=args.electricity_price, gpu_price=args.gpu_price,
            useful_life_years=args.useful_life_years,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"inputs": est.inputs, "tags": est.tags, "results": est.as_dict()}, indent=2))
        return 0
    print(calculator.format_table(est))
    if args.explain:
        print()
        print(calculator.format_breakdown(est))
    else:
        print("\nAdd --explain to see what each number is made of.")
    return 0
