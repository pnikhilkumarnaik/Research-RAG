# PaperMind test guide

Both papers are FICTIONAL, written so you can verify answers against known facts.
Upload all three PDFs in the sidebar and click "Index uploaded PDFs".

## Expected indexing results
| File | Expected |
|---|---|
| 01_fastlora_paper.pdf | Added, ~9 chunks, title "FastLoRA: Low-Rank Adaptation with Adaptive Rank Allocation" |
| 02_sparsegate_paper.pdf | Added, ~9 chunks, title "SparseGate: Mixture-of-Experts Routing with Learned Sparsity" |
| 03_scanned_no_text.pdf | Error: "No extractable text found (is this a scanned PDF?)..." (this is correct behavior) |
| Upload 01 again | "Already indexed" (duplicate detection) |

## Ask tab: factual questions (tick only the paper named)
| Question | Correct answer | Paper |
|---|---|---|
| What average accuracy does FastLoRA reach on NLU-Bench? | 84.3 | FastLoRA |
| How many trainable parameters does FastLoRA train? | About 1.2 million (0.017% of 7B) | FastLoRA |
| What is FastLoRA's total rank budget and how is it used? | 64 across 32 layers (average rank 2) | FastLoRA |
| How long does FastLoRA take to train? | 14 GPU-hours on one A100 | FastLoRA |
| When does FastLoRA become unstable? | When the rank budget is below 32 | FastLoRA |
| How many experts does SparseGate use per layer and how many per token? | 8 experts, top-2 routing | SparseGate |
| How many GPU-hours does SparseGate need? | 412 GPU-hours | SparseGate |
| What happens without the load-balancing loss? | Routing collapse in 5% of runs; accuracy 83.4 in runs that converge | SparseGate |
| What is SparseGate's inference throughput gain? | 1.9x the dense model | SparseGate |

Check that: the cited [n] sources show the right section and page (e.g. the 84.3 answer should cite "5 Results" or "Abstract").

## Ask tab: grounding checks (should NOT be answered from the papers)
- "What is the capital of France?" or "Who won the 2022 World Cup?" -> should say the excerpts don't contain the answer.
- "What GPU memory does FastLoRA need?" -> not stated; a good answer says it isn't in the paper.

## Ask tab: follow-up (uses chat history)
1. "What does SparseGate score on NLU-Bench?" -> 86.1
2. "And how does that compare to the dense baseline?" -> baseline 85.0, gain of 1.1

## Compare tab (select both papers)
Aspect: "accuracy and training cost". Expected: SparseGate more accurate (86.1 vs 84.3), FastLoRA far cheaper (14 vs 412 GPU-hours). Both use NLU-Bench and a 7B base.
Aspect: "limitations". Expected: FastLoRA unstable below budget 32, English only; SparseGate needs full memory, communication overhead, high training cost.

## Summarize tab
Pick each paper. Check the TL;DR contains the headline numbers (84.3 / 86.1) and the limitations match section 6.

## Notes tab
Click "Save as note" on an answer, then "Export all notes (.md)".

## Real papers (run on your own computer)
In the sidebar's "arXiv URL or id" box try: `1706.03762` (Attention Is All You Need), `1810.04805` (BERT), `2005.11401` (the RAG paper), `2106.09685` (LoRA).
