import os
import subprocess
import xml.etree.ElementTree as ET
import json
from server import suggest_tests, git_add_all, git_commit, git_push

report_path = os.path.join("java_agent", "target", "site", "jacoco", "jacoco.xml")

def run_maven_tests():
    """Run mvn test and return exit code + output."""
    try:
        result = subprocess.run(["mvn", "test"], capture_output=True, text=True)
        print(result.stdout)
        return result.returncode
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

def parse_coverage():
    """Parse JaCoCo XML report and return coverage stats."""
    if not os.path.exists(report_path):
        print("JaCoCo report not found. Run mvn test first.")
        return None

    tree = ET.parse(report_path)
    root = tree.getroot()
    counters = root.findall("counter")

    stats = {c.get("type"): {"covered": int(c.get("covered")), "missed": int(c.get("missed"))}
             for c in counters}

    total_covered = sum(v["covered"] for v in stats.values())
    total_missed = sum(v["missed"] for v in stats.values())
    coverage = total_covered / (total_covered + total_missed) * 100 if (total_covered + total_missed) > 0 else 0

    return {"coverage": round(coverage, 2), "stats": stats}

def improve_tests(java_project="java_agent"):
    """Run test improvement cycle."""
    print("\n--- Running Intelligent Test Improvement ---\n")

    # Step 1: Run mvn test
    os.chdir("java_agent")
    run_maven_tests()
    os.chdir("..")

    # Step 2: Parse JaCoCo coverage
    coverage = parse_coverage()
    if not coverage:
        print("Coverage report missing.")
        return

    print(f"Current coverage: {coverage['coverage']}%")

    # Step 3: Identify uncovered methods via suggest_tests
    from server import suggest_tests
    suggestions = suggest_tests(java_project)
    print(json.dumps(suggestions, indent=2))

    # Step 4: Create placeholder test files for uncovered methods
    test_dir = os.path.join(java_project, "src", "test", "java", "generated")
    os.makedirs(test_dir, exist_ok=True)
    for suggestion in suggestions.get("test_suggestions", []):
        test_path = os.path.join(test_dir, f"{suggestion['suggested_test_name']}.java")
        with open(test_path, "w") as f:
            f.write(suggestion["template"])
        print(f"Generated test: {test_path}")

    # Step 5: Commit and push improvements
    git_add_all()
    git_commit(f"Auto-generated {len(suggestions['test_suggestions'])} tests for uncovered methods")
    git_push()

    print("\n Test improvement iteration complete!\n")

if __name__ == "__main__":
    improve_tests()