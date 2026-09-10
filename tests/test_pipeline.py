import tempfile
import unittest
from pathlib import Path

from tajik_benchmark.models import BenchmarkItem
from tajik_benchmark.audit import audit_items, stratified_review_sample
from tajik_benchmark.planning import build_plan
from tajik_benchmark.prompts import render_prompt
from tajik_benchmark.scoring import response_quality_flags
from tajik_benchmark.statistics import summarize_efficiency, wilson_interval
from tajik_benchmark.runner import estimate_cost, run_plan
from tajik_benchmark.dashboard import build_dashboard
from tajik_benchmark.inference import confirmatory_report, holm_adjust, mcnemar_exact, paired_binary_comparison, weighted_kappa
from tajik_benchmark.validation import validate_items


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.item = BenchmarkItem(
            item_id="TG-GRAM-001", split="dev", category="grammar", register="formal", subtype="agreement",
            prompt_tg="Кадом ҷумла дуруст аст?", option_a="Ман меравам.",
            option_b="Ман меравад.", gold_answer="A",
        )

    def test_valid_grammar_item(self):
        self.assertEqual(validate_items([self.item]), [])

    def test_prompt_contains_choices(self):
        prompt = render_prompt(self.item, "direct_tajik")
        self.assertIn("A: Ман меравам.", prompt)
        self.assertIn("B: Ман меравад.", prompt)

    def test_test_split_locked(self):
        test_item = BenchmarkItem(**{**self.item.to_dict(), "split": "test"})
        config = {
            "study_id": "x", "dataset_version": "1", "splits": ["test"],
            "conditions": ["direct_tajik"],
            "models": [{"provider": "mock", "model": "m", "temperature": 0.0, "max_output_tokens": 10}],
        }
        with self.assertRaises(PermissionError):
            build_plan([test_item], config)

    def test_plan_is_deterministically_identified(self):
        config = {
            "study_id": "x", "dataset_version": "1", "splits": ["dev"], "random_seed": 1,
            "conditions": ["direct_tajik"],
            "models": [{"provider": "mock", "model": "m", "temperature": 0.0, "max_output_tokens": 10}],
        }
        first = build_plan([self.item], config)[0]
        second = build_plan([self.item], config)[0]
        self.assertEqual(first.request_hash, second.request_hash)
        self.assertEqual(first.request_id, second.request_id)

    def test_wilson_interval(self):
        low, high = wilson_interval(8, 10)
        self.assertLess(low, 0.8)
        self.assertGreater(high, 0.8)

    def test_current_full_dataset_split_is_valid(self):
        item = BenchmarkItem(**{**self.item.to_dict(), "split": "development"})
        self.assertEqual(validate_items([item]), [])

    def test_primary_test_is_locked(self):
        item = BenchmarkItem(**{**self.item.to_dict(), "split": "primary_test"})
        config = {
            "study_id": "x", "dataset_version": "1", "splits": ["primary_test"],
            "conditions": ["direct_tajik"],
            "models": [{"provider": "mock", "model": "exact-v1", "temperature": 0, "max_output_tokens": 10}],
        }
        with self.assertRaises(PermissionError):
            build_plan([item], config)

    def test_stratified_sample_and_deterministic_randomization(self):
        items = []
        for i in range(16):
            category = "grammar" if i < 8 else "factual"
            register = "formal" if i % 2 == 0 else "conversational"
            items.append(BenchmarkItem(
                item_id=f"I-{i}", split="development", category=category, register=register,
                subtype="x", prompt_tg=f"Саволи {i}", option_a="A1" if category == "grammar" else "",
                option_b="B1" if category == "grammar" else "", gold_answer="A" if category == "grammar" else "ҷавоб",
            ))
        config = {
            "study_id": "x", "dataset_version": "1", "splits": ["development"], "sample_size": 8,
            "random_seed": 7, "conditions": ["direct_tajik"],
            "models": [{"provider": "mock", "model": "m", "temperature": 0, "max_output_tokens": 10}],
        }
        first = build_plan(items, config)
        second = build_plan(items, config)
        self.assertEqual([x.request_id for x in first], [x.request_id for x in second])
        self.assertEqual(len(first), 8)
        self.assertEqual(len({(x.item.category, x.item.register) for x in first}), 4)

    def test_audit_detects_cross_split_duplicates(self):
        other = BenchmarkItem(**{**self.item.to_dict(), "item_id": "TWO", "split": "primary_test"})
        report = audit_items([self.item, other])
        self.assertEqual(len(report["exact_duplicate_groups"]), 1)
        self.assertEqual(report["exact_duplicate_groups"][0]["splits"], ["dev", "primary_test"])

    def test_review_sample_has_decision_fields(self):
        row = stratified_review_sample([self.item], per_cell=1)[0]
        self.assertIn("review_status", row)
        self.assertIn("corrected_text", row)

    def test_format_violation_for_verbose_grammar_answer(self):
        flags = response_quality_flags(self.item.to_dict(), "The answer is A")
        self.assertTrue(flags["format_violation"])

    def test_efficiency_summary(self):
        rows = [{"model":"m", "condition":"direct_tajik", "total_tokens":"10", "latency_ms":"20", "estimated_cost_usd":"0.01", "objective_correct":"1", "format_violation":"false", "request_status":"ok"}]
        summary = summarize_efficiency(rows)[0]
        self.assertEqual(summary["total_tokens"], 10)
        self.assertEqual(summary["failure_count"], 0)

    def test_cost_uses_cached_rate(self):
        pricing = {"models": {"m": {"input_per_million": 2, "cached_input_per_million": 0.2, "output_per_million": 10}}}
        usage = {"input_tokens": 1000, "cached_tokens": 200, "output_tokens": 100}
        self.assertAlmostEqual(estimate_cost(usage, "m", pricing), 0.00264)

    def test_real_runner_supports_resume_with_mock(self):
        with tempfile.TemporaryDirectory() as folder:
            plan = Path(folder) / "plan.jsonl"
            output = Path(folder) / "raw.jsonl"
            request = {
                "request_id": "r1", "request_hash": "h1", "rendered_prompt": "test prompt",
                "model": {"provider": "mock", "model": "m", "temperature": 0, "max_output_tokens": 10},
                "item": {"category": "grammar", "gold_answer": "A"},
            }
            plan.write_text(__import__("json").dumps(request) + "\n", encoding="utf-8")
            pricing = {"snapshot_date": "x", "models": {"m": {"input_per_million": 1, "output_per_million": 1}}}
            first = run_plan(str(plan), str(output), pricing)
            second = run_plan(str(plan), str(output), pricing, resume=True)
            self.assertEqual(first["succeeded"], 1)
            self.assertEqual(second["skipped_completed"], 1)

    def test_dashboard_does_not_embed_responses(self):
        with tempfile.TemporaryDirectory() as folder:
            scores = Path(folder) / "scores.csv"
            dashboard = Path(folder) / "index.html"
            scores.write_text(
                "provider,model,condition,category,objective_correct,total_tokens,estimated_cost_usd,latency_ms,request_status,response_text\n"
                "mock,m,direct_tajik,grammar,1,10,0.01,20,ok,SECRET RESPONSE\n", encoding="utf-8"
            )
            build_dashboard(str(scores), str(dashboard))
            page = dashboard.read_text(encoding="utf-8")
            self.assertIn("Tajik LLM Benchmark", page)
            self.assertNotIn("SECRET RESPONSE", page)

    def test_mcnemar_and_holm(self):
        self.assertAlmostEqual(mcnemar_exact(0, 5)["p_value"], 0.0625)
        adjusted = holm_adjust([0.01, 0.04, 0.03])
        self.assertEqual(len(adjusted), 3)
        self.assertTrue(all(0 <= p <= 1 for p in adjusted))

    def test_paired_binary_comparison(self):
        rows = [
            {"model": "m", "item_id": "1", "condition": "direct", "objective_correct": "0"},
            {"model": "m", "item_id": "1", "condition": "pivot", "objective_correct": "1"},
            {"model": "m", "item_id": "2", "condition": "direct", "objective_correct": "1"},
            {"model": "m", "item_id": "2", "condition": "pivot", "objective_correct": "1"},
        ]
        result = paired_binary_comparison(rows, "direct", "pivot", bootstrap_samples=100)
        self.assertEqual(result["n_pairs"], 2)
        self.assertEqual(result["difference_percentage_points"], 50)

    def test_weighted_kappa_perfect_agreement(self):
        self.assertEqual(weighted_kappa([(0, 0), (1, 1), (2, 2)]), 1.0)

    def test_confirmatory_report_is_model_specific(self):
        rows = []
        for model in ("a", "b"):
            rows.extend([
                {"model": model, "item_id": "1", "category": "grammar", "condition": "direct_tajik", "objective_correct": "0"},
                {"model": model, "item_id": "1", "category": "grammar", "condition": "pivot_persian", "objective_correct": "1"},
            ])
        report = confirmatory_report(rows)
        self.assertEqual({r["model"] for r in report}, {"a", "b"})


if __name__ == "__main__":
    unittest.main()
