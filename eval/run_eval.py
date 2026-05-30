# eval/run_eval.py
#
# Runs the evaluation dataset against the live API and produces a score report.
# Run this with the backend server running on port 8000.
#
# Usage: uv run python eval/run_eval.py

import json
import requests
import os

API_BASE  = "http://localhost:8000"
EVAL_FILE = os.path.join(os.path.dirname(__file__), "test_cases.json")


def load_test_cases() -> list[dict]:
    with open(EVAL_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["test_cases"]


def run_test(case: dict) -> dict:
    """Runs a single test case against the API and returns result."""
    try:
        response = requests.post(
            f"{API_BASE}/chat",
            json={
                "message":      case["input"],
                "history":      [],
                "denomination": case["denomination"]
            },
            timeout=60
        )
        result = response.json()

        # Check if type matches expected
        type_match = result["type"] == case["expected_type"]

        return {
            "id":          case["id"],
            "category":    case["category"],
            "input":       case["input"][:60] + "...",
            "expected":    case["expected_type"],
            "got":         result["type"],
            "type_match":  type_match,
            "verified":    result.get("verified", None),
            "pass":        type_match,
            "error":       None
        }

    except Exception as e:
        return {
            "id":         case["id"],
            "category":   case["category"],
            "input":      case["input"][:60] + "...",
            "expected":   case["expected_type"],
            "got":        "ERROR",
            "type_match": False,
            "verified":   None,
            "pass":       False,
            "error":      str(e)
        }


def main():
    print("=" * 65)
    print("CHRISTIANITY AI — EVALUATION RUNNER")
    print("=" * 65)

    # Check server is running
    try:
        requests.get(f"{API_BASE}/health", timeout=5)
    except Exception:
        print("ERROR: Backend server not running on port 8000.")
        print("Start it with: uv run python backend/main.py")
        return

    cases   = load_test_cases()
    results = []
    by_category = {}

    for i, case in enumerate(cases):
        print(f"Running {case['id']} ({i+1}/{len(cases)})...", end=" ", flush=True)
        result = run_test(case)
        results.append(result)

        icon = "✅" if result["pass"] else "❌"
        print(f"{icon} [{result['got'].upper():8}] expected={result['expected']}")

        cat = case["category"]
        if cat not in by_category:
            by_category[cat] = {"pass": 0, "fail": 0}
        if result["pass"]:
            by_category[cat]["pass"] += 1
        else:
            by_category[cat]["fail"] += 1

    # Summary
    total  = len(results)
    passed = sum(1 for r in results if r["pass"])
    failed = total - passed

    print()
    print("=" * 65)
    print("RESULTS BY CATEGORY")
    print("=" * 65)
    for cat, counts in by_category.items():
        cat_total = counts["pass"] + counts["fail"]
        print(f"  {cat:20} {counts['pass']}/{cat_total} passed")

    print()
    print("=" * 65)
    print(f"OVERALL: {passed}/{total} passed  ({round(passed/total*100)}%)")
    print("=" * 65)

    # Save results
    out_path = os.path.join(os.path.dirname(__file__), "eval_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "total":  total,
            "passed": passed,
            "failed": failed,
            "score":  f"{round(passed/total*100)}%",
            "results": results
        }, f, indent=2)
    print(f"Full results saved to: {out_path}")


if __name__ == "__main__":
    main()