import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

# Try to support being used as an MCP tool, but allow running standalone.
try:
    from fastmcp import FastMCP
    mcp = FastMCP(name="java_test_runner")
    def tool():
        return mcp.tool()
except Exception:
    # fallback no-op decorator
    def tool():
        def decorator(f):
            return f
        return decorator


def parse_jacoco_xml(xml_path: Path) -> dict:
    """Parse JaCoCo XML report into structured coverage data."""
    coverage = {
        "instructions": None,
        "branches": None,
        "lines": None,
        "methods": None,
        "classes": None
    }

    if not xml_path.exists():
        return coverage

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        counters = root.findall(".//counter")

        # Collect coverage data for each metric
        for c in counters:
            ctype = c.attrib.get("type")
            covered = int(c.attrib.get("covered", 0))
            missed = int(c.attrib.get("missed", 0))
            total = covered + missed
            pct = round((covered / total * 100), 2) if total > 0 else 0.0
            if ctype and ctype.lower() in coverage:
                coverage[ctype.lower()] = pct

        return coverage

    except Exception as e:
        return {"error": f"Failed to parse JaCoCo XML: {e}"}


@tool()
def run_maven_tests(project_path: str = "java_agent") -> dict:
    """
    Run 'mvn clean verify' inside the project and return structured test + coverage data.
    """
    try:
        # Run tests with JaCoCo instrumentation
        result = subprocess.run(
            ["mvn", "clean", "verify"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=120
        )

        # Parse JaCoCo XML report
        jacoco_xml = Path(project_path) / "target" / "site" / "jacoco" / "jacoco.xml"
        coverage_data = parse_jacoco_xml(jacoco_xml)

        # Aggregate coverage percent if available
        valid_values = [v for v in coverage_data.values() if isinstance(v, (int, float))]
        overall = round(sum(valid_values) / len(valid_values), 2) if valid_values else 0.0

        return {
            "exit_code": result.returncode,
            "coverage_percent": overall,
            "coverage": coverage_data,
            "stdout": result.stdout[-800:],  # last 800 chars for compactness
            "stderr": result.stderr[-800:]
        }

    except subprocess.TimeoutExpired:
        return {"error": "Maven test run timed out"}


import re


def find_uncovered_methods(xml_path: str) -> list:
    """
    Scan JaCoCo XML and return a list of methods with 0% coverage.
    Each entry contains package, class, and method names.
    """
    uncovered = []
    try:
        xml_p = Path(xml_path)
        if not xml_p.exists():
            return uncovered

        tree = ET.parse(xml_p)
        root = tree.getroot()

        # JaCoCo XML structure: report -> package -> class -> method -> counter
        for pkg in root.findall('.//package'):
            pkg_name = pkg.get('name')
            for cls in pkg.findall('class'):
                cls_name = cls.get('name')
                for method in cls.findall('method'):
                    method_name = method.get('name')
                    # gather counters for this method
                    counters = {c.get('type'): (int(c.get('missed', '0')), int(c.get('covered', '0'))) for c in method.findall('counter')}
                    instr_missed, instr_covered = counters.get('INSTRUCTION', (0, 0))
                    total = instr_missed + instr_covered
                    coverage = 0 if total == 0 else round(instr_covered / total * 100, 2)
                    if coverage == 0:
                        uncovered.append({
                            'package': pkg_name,
                            'class': cls_name,
                            'method': method_name
                        })
        return uncovered
    except Exception as e:
        return [{'error': str(e)}]


@tool()
def suggest_tests(project_path: str = "java_agent") -> dict:
    """
    Runs JaCoCo via `run_maven_tests` and returns a list of uncovered methods with suggested JUnit tests.
    """
    from pathlib import Path

    # ensure tests and report are generated
    result = run_maven_tests(project_path)

    jacoco_xml = Path(project_path) / 'target' / 'site' / 'jacoco' / 'jacoco.xml'
    uncovered = find_uncovered_methods(str(jacoco_xml))

    suggestions = []
    for entry in uncovered:
        if 'error' in entry:
            continue
        cls = entry.get('class', 'Unknown')
        method = entry.get('method', 'Unknown')
        # derive a short class name for template if package-like path present
        short_cls = cls.split('/')[-1].split('$')[-1]
        test_name = f"test_{method}"
        template = f"@Test\nvoid {test_name}() {{\n    {short_cls}.{method}();\n    // TODO: Add assertions\n}}"
        suggestions.append({
            'class': cls,
            'method': method,
            'suggested_test_name': test_name,
            'template': template
        })

    # attach findings to result and return
    result['uncovered_methods'] = uncovered
    result['test_suggestions'] = suggestions
    return result
