import os
import subprocess
import xml.etree.ElementTree as ET
import json
from server import suggest_tests, git_add_all, git_commit, git_push

JAVA_PROJECT = "java_agent"
REPORT_XML = os.path.join(JAVA_PROJECT, "target", "site", "jacoco", "jacoco.xml")


def run_maven_tests():
    print("\n--- Running mvn test ---\n")
    result = subprocess.run(
        ["mvn", "test"],
        cwd=JAVA_PROJECT,
        capture_output=True,
        text=True
    )
    print(result.stdout)
    return result.returncode


def parse_coverage():
    if not os.path.exists(REPORT_XML):
        print("❌ JaCoCo report missing.")
        return None

    tree = ET.parse(REPORT_XML)
    counters = tree.getroot().findall("counter")

    stats = {}
    total_covered = 0
    total_missed = 0

    for c in counters:
        t = c.get("type")
        covered = int(c.get("covered"))
        missed = int(c.get("missed"))
        stats[t] = {"covered": covered, "missed": missed}
        total_covered += covered
        total_missed += missed

    pct = total_covered / (total_covered + total_missed) * 100 if total_covered + total_missed else 0
    return {"coverage": round(pct, 2), "stats": stats}


def sanitize_method_name(method):
    """Fix method names so they are valid Java identifiers."""
    if method == "<init>":
        return "constructor"
    return method.replace("<", "").replace(">", "").replace("/", "_")


def generate_test_file(suggestion):
    pkg = suggestion["class"].rsplit(".", 1)[0]
    class_name = suggestion["class"].split(".")[-1]
    method = suggestion["method"]

    safe_name = sanitize_method_name(method)
    test_class_name = f"Generated_{safe_name}_Test"

    test_dir = os.path.join(JAVA_PROJECT, "src", "test", "java", "generated")
    os.makedirs(test_dir, exist_ok=True)

    file_path = os.path.join(test_dir, f"{test_class_name}.java")

    template = f"""
package generated;

import org.junit.jupiter.api.Test;
import {pkg}.{class_name};

public class {test_class_name} {{

    @Test
    void test_{safe_name}() {{
        {class_name} obj = new {class_name}();
        // TODO: improve this test
    }}
}}
"""

    with open(file_path, "w") as f:
        f.write(template)

    print(f"✔ Generated: {file_path}")


def improve_tests():
    print("\n=== Running Phase 4: Intelligent Test Improvement ===")

    # Step 1 — run tests
    run_maven_tests()

    # Step 2 — parse coverage
    coverage = parse_coverage()
    if not coverage:
        print("❌ Coverage missing.")
        return

    print(f"📊 Current Coverage: {coverage['coverage']}%")

    # Step 3 — generate suggestions
    suggestions = suggest_tests(JAVA_PROJECT)
    print(json.dumps(suggestions, indent=2))

    # Step 4 — generate real Java test classes
    for s in suggestions.get("test_suggestions", []):
        generate_test_file(s)

    # Step 5 — commit & push
    git_add_all()
    git_commit("Auto-generated improved JUnit tests")
    git_push()

    print("\n🎉 Phase 4 test improvement cycle complete!\n")


if __name__ == "__main__":
    improve_tests()