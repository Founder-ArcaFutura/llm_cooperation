OLMo-2 7B: behavioral-only pretraining trajectory
================================================

Requirements: use the same G:\llm_cooperation checkout and frozen Phase 0B bank
that were used for the previous 1B study.

1. Extract both .py files into G:\llm_cooperation.
2. Confirm huggingface_hub is installed (pip install huggingface_hub if needed).
3. Resolve and pin the five published OLMo 2 7B checkpoints, without GPU use:

   python .\prepare_olmo7b_checkpoints.py

   IMPORTANT: Review the printed tags and SHAs. A zero-token ref may not exist.
   The Stage 2 endpoint uses ingredient3, NOT the souped main checkpoint.

4. Pilot test ONLY checkpoint 0 with the exploratory Phase 0B split:

   modal run --env main .\modal_olmo7b_behavior_only.py --checkpoint-order 0 --split exploratory --authorize-paid-run

   The GPU is a 48GB L40S, to avoid memory risk with 7B.
   This costs money and may download ~29GB per unique 7B checkpoint to shared cache.

5. After reviewing the first result, run other 7B checkpoints one by one:

   foreach ($i in 1..4) {
       modal run --env main .\modal_olmo7b_behavior_only.py --checkpoint-order $i --split exploratory --authorize-paid-run
   }

6. Store run records separately in existing Modal volume under
   olmo2-7b-behavioral-emergence-v1.
   To download, PRE-CREATE the destination directory:

   New-Item -ItemType Directory -Force .\olmo7b_behavior_results | Out-Null
   modal volume get llm-coop-olmo-emergence olmo2-7b-behavioral-emergence-v1 .\olmo7b_behavior_results --env main

Notes: All results are exploratory; no activation capture or linear probing.
Run a calibration/format audit before interpreting apparent cooperation. Existing
OLMo 2 7B completed-base data are NOT the same as the ingredient-3 endpoint.
The script has been syntax-checked but not live-tested on the remote model.
