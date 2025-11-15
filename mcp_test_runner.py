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
