OLMo 2 five-checkpoint behavioral-only runner

1. Place modal_olmo_behavior_only_verified.py in the root of G:\llm_cooperation (the repository).
2. Switch to phase_1a_training_emergence branch (preserve any uncommitted work first).
3. Run exploratory zero-token smoke:
   modal run --env main .\modal_olmo_behavior_only_verified.py --checkpoint-order 0 --split exploratory --authorize-paid-run
4. To run all five on the existing Phase 0B 124-scenario bank:
   modal run --env main .\modal_olmo_behavior_only_verified.py --split all --authorize-paid-run --authorize-confirmatory

This script runs paid GPU inference in Modal after explicit authorization. It is syntax-checked locally but not GPU-tested here. It neither updates the frozen bank nor runs activation probes.

sha256: e707b26e446e509c60974947455c8bc4b801c79233e7e46dea0d8efbffbdb27e
