# server.py
from fastmcp import FastMCP
import math
import os
import subprocess
import json

app = FastMCP(name="SE333 Test Agent")

@app.tool()
def add(a: float, b: float) -> float:
    """Add two numbers"""
    return a + b

@app.tool()
def sqrt(x: float) -> float:
    """Return the square root of x"""
    return math.sqrt(x)


@app.tool()
def run_maven_tests(module: str) -> dict:
    """Run `mvn clean verify` in the given module directory, capture output,
    parse the generated JaCoCo HTML report for overall instruction coverage,
    and return a JSON-serializable dict with exit_code, coverage_percent,
    stdout and stderr.
    """
    import os
    import subprocess
    import re

    result = {
        "exit_code": None,
        "coverage_percent": None,
        "stdout": "",
        "stderr": "",
    }

    # locate module directory relative to current working directory
    module_dir = os.path.join(os.getcwd(), module)
    if not os.path.isdir(module_dir):
        result["exit_code"] = 127
        result["stderr"] = f"Module directory not found: {module_dir}"
        return result

    # run maven
    proc = subprocess.run(["mvn", "clean", "verify"], cwd=module_dir, capture_output=True, text=True)
    result["exit_code"] = proc.returncode
    result["stdout"] = proc.stdout
    result["stderr"] = proc.stderr

    # attempt to parse JaCoCo HTML report for coverage metrics
    report_path = os.path.join(module_dir, "target", "site", "jacoco", "index.html")
    # initialize detailed coverage fields
    result["coverage"] = {
        "instructions": None,
        "branches": None,
        "lines": None,
        "methods": None,
        "classes": None,
    }

    if os.path.isfile(report_path):
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                html = f.read()

            # The JaCoCo total row places percentages in <td class="ctr2"> cells.
            # The order in the table is: (Missed Instructions cell) then instruction Cov (ctr2),
            # then Missed Branches, branch Cov (ctr2), Missed (ctr1) Cxty, Missed (ctr1) Lines, line Cov (ctr2), ...
            # Simpler approach: find the <tfoot> Total row and then grab all occurrences of ctr2 percentages
            tfoot = re.search(r"<tfoot>(.*?)</tfoot>", html, re.S)
            if tfoot:
                pcts = re.findall(r"class=\"ctr2\">\s*([0-9]+(?:\.[0-9]+)?)%\s*</td>", tfoot.group(1))
                # expected order in many JaCoCo templates: [instructions, branches, ???, lines, methods, classes]
                # We'll map by position defensively.
                try:
                    if len(pcts) >= 1:
                        result["coverage"]["instructions"] = float(pcts[0])
                    if len(pcts) >= 2:
                        result["coverage"]["branches"] = float(pcts[1])
                    # lines usually appears at position 3 or 4 depending on template; try to find a plausible lines % (0-100)
                    # We'll search the whole tfoot for 'Lines' label and the following ctr2 percentage nearby as a more robust approach.
                    lines_match = re.search(r"Lines</td>.*?class=\"ctr2\">\s*([0-9]+(?:\.[0-9]+)?)%\s*</td>", tfoot.group(1), re.S)
                    if lines_match:
                        result["coverage"]["lines"] = float(lines_match.group(1))
                    else:
                        # fallback: pick the third pct if available and lines not found
                        if len(pcts) >= 3:
                            result["coverage"]["lines"] = float(pcts[2])

                    # methods
                    methods_match = re.search(r"Methods</td>.*?class=\"ctr2\">\s*([0-9]+(?:\.[0-9]+)?)%\s*</td>", tfoot.group(1), re.S)
                    if methods_match:
                        result["coverage"]["methods"] = float(methods_match.group(1))
                    else:
                        if len(pcts) >= 4:
                            result["coverage"]["methods"] = float(pcts[3])

                    # classes
                    classes_match = re.search(r"Classes</td>.*?class=\"ctr2\">\s*([0-9]+(?:\.[0-9]+)?)%\s*</td>", tfoot.group(1), re.S)
                    if classes_match:
                        result["coverage"]["classes"] = float(classes_match.group(1))
                    else:
                        if len(pcts) >= 5:
                            result["coverage"]["classes"] = float(pcts[4])

                    # if instructions was found, mirror it to top-level coverage_percent for backward compat
                    if result["coverage"]["instructions"] is not None:
                        result["coverage_percent"] = result["coverage"]["instructions"]
                    else:
                        result["coverage_percent"] = 0.0
                except Exception:
                    # any parsing oddities fallback to zeroes
                    result["coverage_percent"] = 0.0
            else:
                result["coverage_percent"] = 0.0
                result["stderr"] += "\nJaCoCo tfoot not found in report."
        except Exception as e:
            result["coverage_percent"] = 0.0
            result["stderr"] += f"\nError parsing report: {e}"
    else:
        # no report produced
        result["coverage_percent"] = 0.0
        if result["exit_code"] == 0:
            result["stderr"] += "\nJaCoCo report not found after a successful build."

    return result

import xml.etree.ElementTree as ET

@app.tool()
def suggest_tests(module: str) -> dict:
    """
    Parse JaCoCo XML report and suggest test methods for uncovered code.
    """
    import os

    report_path = os.path.join(module, "target", "site", "jacoco", "jacoco.xml")
    if not os.path.exists(report_path):
        return {"error": f"JaCoCo report not found at {report_path}"}

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
                    method_name = method.attrib["name"]
                    counters = {c.attrib["type"]: c.attrib for c in method.findall("counter")}
                    instr = counters.get("INSTRUCTION", None)
                    if instr:
                        covered = int(instr["covered"])
                        missed = int(instr["missed"])
                        if covered == 0 and missed > 0:
                            uncovered_methods.append({
                                "package": pkg_name,
                                "class": class_name,
                                "method": method_name
                            })
                            suggestions.append({
                                "class": class_name,
                                "method": method_name,
                                "suggested_test_name": f"test_{method_name}",
                                "template": f"@Test\nvoid test_{method_name}() {{\n    new {class_name}().{method_name}();\n    // TODO: add assertions\n}}"
                            })
    except Exception as e:
        return {"error": str(e)}

    return {
        "uncovered_methods": uncovered_methods,
        "test_suggestions": suggestions
    }



# -------------------------------
# PHASE 3: GIT AUTOMATION TOOLS
# -------------------------------


@app.tool()
def git_status() -> dict:
    """Return the current git status including staged, unstaged, and untracked files."""
    try:
        result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }
    except Exception as e:
        return {"exit_code": 1, "stdout": "", "stderr": str(e)}


@app.tool()
def git_add_all() -> dict:
    """Stage all changes except ignored files and build artifacts."""
    try:
        subprocess.run(["git", "add", "--all"], check=True)
        result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
        return {
            "message": "All changes staged successfully.",
            "stdout": result.stdout.strip()
        }
    except subprocess.CalledProcessError as e:
        return {"message": "Failed to stage files.", "stderr": str(e)}


@app.tool()
def git_commit(message: str = "Automated commit") -> dict:
    """Commit all staged changes with the given message."""
    try:
        result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True)
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }
    except Exception as e:
        return {"exit_code": 1, "stdout": "", "stderr": str(e)}


@app.tool()
def git_push(remote: str = "origin", branch: str = "main") -> dict:
    """Simulate git push (does not actually push for safety)."""
    try:
        # Dry-run only for demo purposes
        result = subprocess.run(["git", "push", "--dry-run", remote, branch], capture_output=True, text=True)
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }
    except Exception as e:
        return {"exit_code": 1, "stdout": "", "stderr": str(e)}


@app.tool()
def git_pull_request(base: str = "main", title: str = "Auto PR", body: str = "Automated Pull Request") -> dict:
    """Mock pull request creation (for demo only)."""
    try:
        current_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True
        ).stdout.strip()
        pr_url = f"https://github.com/YOUR_USERNAME/SE333Finaljguiang/compare/{base}...{current_branch}?expand=1"
        return {
            "message": f"Simulated pull request created for branch '{current_branch}' targeting '{base}'.",
            "url": pr_url
        }
    except Exception as e:
        return {"error": str(e)}
    

# ============================================================
# Phase 5 –  Extensions
# ============================================================

@app.tool()
def spec_based_tester(java_file: str) -> dict:
    """
    Generate boundary-value and equivalence-class test suggestions
    for public numeric methods in a Java source file.
    """
    import re, os
    result = {"file": java_file, "tests": []}
    if not os.path.isfile(java_file):
        return {"error": f"File not found: {java_file}"}

    with open(java_file, "r", encoding="utf-8") as f:
        src = f.read()

    # Very simple parse for 'public <type> <method>(<params>)'
    matches = re.findall(r"public\s+[\w<>]+\s+(\w+)\s*\(([^)]*)\)", src)
    for method, params in matches:
        numeric_params = [p for p in params.split(",") if any(t in p for t in ["int", "double", "float", "long"])]
        if not numeric_params:
            continue
        param_names = [p.split()[-1] for p in numeric_params if p.strip()]
        template = [f"@Test\nvoid test_{method}_boundaries() {{"]

        for name in param_names:
            template.append(f"    // Boundary tests for {name}")
            template.append(f"    new {os.path.basename(java_file).replace('.java','')}().{method}({name}_MIN);")
            template.append(f"    new {os.path.basename(java_file).replace('.java','')}().{method}({name}_MID);")
            template.append(f"    new {os.path.basename(java_file).replace('.java','')}().{method}({name}_MAX);")

        template.append("}")
        result["tests"].append({"method": method, "template": "\n".join(template)})
    return result


@app.tool()
def code_review_agent(java_dir: str) -> dict:
    """
    Perform lightweight static analysis on Java files.
    Flags long methods, nested loops, and missing documentation.
    """
    import os, re
    issues = []
    for root, _, files in os.walk(java_dir):
        for f in files:
            if f.endswith(".java"):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8") as j:
                    code = j.read()

                # Detect long methods
                for m in re.finditer(r"(public|private|protected)\s+[\w<>]+\s+\w+\s*\([^)]*\)\s*\{", code):
                    start = m.end()
                    end = code.find("}", start)
                    body = code[start:end]
                    if body.count("\n") > 30:
                        issues.append({"file": path, "issue": "Long method (>30 lines)", "snippet": m.group(0)})

                # Missing Javadoc
                for decl in re.finditer(r"public\s+[\w<>]+\s+\w+\s*\(", code):
                    before = code[:decl.start()]
                    if not before.strip().endswith("*/"):
                        issues.append({"file": path, "issue": "Missing Javadoc", "snippet": decl.group(0)})

                # Nested loops
                if re.search(r"for\s*\(.*\)\s*{[^}]*for\s*\(", code, re.S):
                    issues.append({"file": path, "issue": "Nested loop detected"})

    return {"dir": java_dir, "issues": issues}

if __name__ == "__main__":
    import logging
    import time
    logging.basicConfig(level=logging.INFO)
    print("Starting FastMCP server on http://127.0.0.1:8000 ...")
    try:
        app.run(transport="sse")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n Server stopped by user.")