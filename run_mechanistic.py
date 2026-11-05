"""Run the same exploratory screen on a local GPU after explicit authorization."""
import argparse
from llm_cooperation.mechanistic.screen import run
from llm_cooperation.mechanistic.analyze import summarize

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--model', required=True)
    p.add_argument('--revision', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--top-k', type=int, default=10)
    p.add_argument('--authorize-inference', action='store_true')
    args = p.parse_args()
    if not args.authorize_inference:
        p.error('Inference requires --authorize-inference')
    run(args.model, args.revision, args.output, args.top_k)
    print(summarize(args.output))
