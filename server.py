# server.py
from fastmcp import FastMCP
import math
import os
import subprocess
import json
import xml.etree.ElementTree as ET

app = FastMCP(name="SE333 Test Agent")

# ============================================================
# Phase 1 — Calculator Tools
# ============================================================

@app.tool(description="Add two numbers and return the result.")
def add(a: float, b: float) -> float:
    return a + b

@app.tool(description="Compute the square root of a number.")
def sqrt(x: float) -> float:
    return math.sqrt(x)


# ============================================================
# Phase 2 — Maven & Coverage Tools
# ============================================================

@app.tool(description="Run mvn clean verify and return JaCoCo coverage + logs.")
def run_maven_tests(module: str) -> dict:
    result = {
        "exit_code": None,
        "coverage_percent": None,
        "stdout": "",
        "stderr": "",
        "coverage": {}
    }

    module_dir = os.path.join(os.getcwd(), module)
    if not os.path.isdir(module_dir):
        return {"error": f"Module not found: {module_dir}"}

    # Run Maven
    proc = subprocess.run(
        ["mvn", "clean", "verify"],
        cwd=module_dir,
        capture_output=True,
        text=True
    )

    result["exit_code"] = proc.returncode
    result["stdout"] = proc.stdout
    result["stderr"] = proc.stderr

    # Parse JaCoCo
    report_path = os.path.join(module_dir, "target", "site", "jacoco", "jacoco.xml")

    if not os.path.exists(report_path):
        result["coverage_percent"] = 0.0
        result["stderr"] += "\nJaCoCo report not found"
        return result

    try:
        tree = ET.parse(report_path)
        root = tree.getroot()

        counters = {
            c.attrib["type"]: {
                "covered": int(c.attrib["covered"]),
                "missed": int(c.attrib["missed"])
            }
            for c in root.findall("counter")
        }

        covered = sum(v["covered"] for v in counters.values())
        missed = sum(v["missed"] for v in counters.values())
        total = covered + missed

        pct = (covered / total) * 100 if total > 0 else 0

        result["coverage"] = counters
        result["coverage_percent"] = round(pct, 2)

    except Exception as e:
        result["coverage_percent"] = 0.0
        result["stderr"] += f"\nError parsing JaCoCo XML: {e}"

    return result


@app.tool(description="Analyze JaCoCo XML to find uncovered methods and suggest tests.")
def suggest_tests(module: str) -> dict:
    report_path = os.path.join(module, "target", "site", "jacoco", "jacoco.xml")
    if not os.path.exists(report_path):
        return {"error": f"JaCoCo report missing at {report_path}"}

    uncovered_methods = []
    suggestions = []

    try:
        tree = ET.parse(report_path)
        root = tree.getroot()

        for pkg in root.findall(".//package"):
            pkg_name = pkg.attrib["name"]

            for clazz in pkg.findall("class"):
                class_name = clazz.attrib["name"]

                for method in clazz.findall("method"):
                    mname = method.attrib["name"]

                    counter = method.find("counter[@type='INSTRUCTION']")
                    if counter is None:
                        continue

                    covered = int(counter.attrib["covered"])
                    missed = int(counter.attrib["missed"])

                    # Only suggest tests for missed == 100%
                    if covered == 0 and missed > 0:
                        test_name = f"test_{mname}"

                        uncovered_methods.append({
                            "package": pkg_name,
                            "class": class_name,
                            "method": mname
                        })

                        suggestions.append({
                            "class": class_name,
                            "method": mname,
                            "suggested_test_name": test_name,
                            "template": (
                                "@Test\n"
                                f"void {test_name}() {{\n"
                                f"    new {class_name}().{mname}();\n"
                                "    // TODO: add assertions\n"
                                "}"
                            )
                        })
    except Exception as e:
        return {"error": str(e)}

    return {
        "uncovered_methods": uncovered_methods,
        "test_suggestions": suggestions
    }


# ============================================================
# Phase 3 — Git Automation Tools
# ============================================================

@app.tool(description="Show modified, staged, and untracked files.")
def git_status() -> dict:
    try:
        r = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
        return {"stdout": r.stdout, "stderr": r.stderr, "exit_code": r.returncode}
    except Exception as e:
        return {"error": str(e)}


@app.tool(description="Stage all modified files in the repository.")
def git_add_all() -> dict:
    try:
        subprocess.run(["git", "add", "--all"], check=True)
        r = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
        return {"message": "Staged all files.", "stdout": r.stdout}
    except Exception as e:
        return {"error": str(e)}


@app.tool(description="Commit staged changes with the provided commit message.")
def git_commit(message: str = "Automated commit") -> dict:
    try:
        r = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True)
        return {"stdout": r.stdout, "stderr": r.stderr, "exit_code": r.returncode}
    except Exception as e:
        return {"error": str(e)}


@app.tool(description="Simulate git push (dry-run for safety).")
def git_push(remote: str = "origin", branch: str = "main") -> dict:
    try:
        r = subprocess.run(["git", "push", "--dry-run", remote, branch],
                           capture_output=True, text=True)
        return {"stdout": r.stdout, "stderr": r.stderr, "exit_code": r.returncode}
    except Exception as e:
        return {"error": str(e)}


@app.tool(description="Simulate pull request creation and return URL.")
def git_pull_request(base: str = "main", title: str = "Auto PR", body: str = "Automated PR") -> dict:
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True
        ).stdout.strip()

        pr_url = f"https://github.com/YOUR_USERNAME/SE333Finaljguiang/compare/{base}...{branch}?expand=1"
        return {"message": "Simulated PR created.", "url": pr_url}

    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Phase 5 — Creative Extensions
# ============================================================

@app.tool(description="Generate boundary-value and equivalence-class tests for numeric Java methods.")
def spec_based_tester(java_file: str) -> dict:
    import re

    result = {"file": java_file, "tests": []}

    if not os.path.isfile(java_file):
        return {"error": f"File not found: {java_file}"}

    with open(java_file, "r", encoding="utf-8") as f:
        src = f.read()

    matches = re.findall(r"public\s+[\w<>]+\s+(\w+)\s*\(([^)]*)\)", src)

    for method, params in matches:
        numeric = [p for p in params.split(",") if any(t in p for t in ["int", "double", "float", "long"])]

        if not numeric:
            continue

        template = ["@Test", f"void test_{method}_boundaries() {{"]

        for p in numeric:
            pname = p.split()[-1]
            template.append(f"    // Boundary tests for {pname}")
            template.append(f"    // TODO: Call {method} with MIN/MID/MAX")

        template.append("}")

        result["tests"].append({
            "method": method,
            "template": "\n".join(template)
        })

    return result


@app.tool(description="Perform lightweight static analysis for long methods, missing Javadoc, and nested loops.")
def code_review_agent(java_dir: str) -> dict:
    import re

    issues = []

    for root, _, files in os.walk(java_dir):
        for f in files:
            if not f.endswith(".java"):
                continue

            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8") as j:
                code = j.read()

            # Missing Javadoc
            for decl in re.finditer(r"public\s+[\w<>]+\s+\w+\s*\(", code):
                before = code[:decl.start()]
                if not before.strip().endswith("*/"):
                    issues.append({"file": path, "issue": "Missing Javadoc"})

            # Long methods
            for m in re.finditer(r"(public|private|protected).*?\\{", code):
                start = m.end()
                end = code.find("}", start)
                if end != -1:
                    body = code[start:end]
                    if body.count("\n") > 30:
                        issues.append({"file": path, "issue": "Long method (>30 lines)"})

            # Nested loops
            if re.search(r"for\s*\(.*\).*?for\s*\(", code, re.S):
                issues.append({"file": path, "issue": "Nested loop detected"})

    return {"dir": java_dir, "issues": issues}


# ============================================================
# Run server
# ============================================================

if __name__ == "__main__":
    print("Starting FastMCP server on http://127.0.0.1:8000 ...")
    app.run("sse")