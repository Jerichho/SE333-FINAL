Jericho Guiang

SE333 Final Project - AI-Driven Testing Agent (MCP)

Overview:

This project implements an AI-powered intelligent testing agent using the Model Context Protocol (MCP).

    The agent is capable of:
        • Analyzing Java Maven projects
        • Automatically generating & improving JUnit tests
        • Running Maven builds and collecting JaCoCo coverage
        • Iteratively increasing code coverage
        • Automatically committing/pushing improvements via Git
        • Running creative extension tools (specification testing + AI code review)

⸻⸻⸻

Installation & Environment Setup:

1. Clone the repository

    git clone https://github.com/Jerichho/SE333-FINAL
    cd SE333-FINAL


⸻⸻⸻

2. Install system prerequisites:

    You must have:
        • VS Code 
        • Node.js 18+
        • Git
        • Java 11+
        • Maven 3.6+
        • Python 3.10+
        • uv package manager 

⸻⸻⸻

3. Configure Python environment:

    uv init
    uv venv
    source .venv/bin/activate   # Windows: .venv\Scripts\activate
    uv add mcp[cli] httpx fastmcp


⸻⸻⸻

4. Start the MCP server:

    python3 server.py

    Expected output:

    Starting FastMCP server on http://127.0.0.1:8000 ...


⸻⸻⸻

5. Connect to VS Code:

        1. Press CTRL + SHIFT + P
        2. Choose MCP: Add Server
        3. Enter: http://127.0.0.1:8000
        4. Name it: SE333 Test Agent
        5. Verify tools appear in Chat sidebar.

⸻⸻⸻

6. Enable YOLO Mode (Auto-Approve):

        1. CTRL + SHIFT + P
        2. “Chat: Settings”
        3. Enable Auto-Approve
        4. Under Auto-Approve Commands, add:

mvn test


⸻⸻⸻

7. Add agent prompt:

Create:

    .github/prompts/tester.prompt.md

Format:

    mode: "agent"
    tools: ["run_maven_tests", "suggest_tests", "git_status", "git_add_all", "git_commit", "git_push"]
    description: "SE333 automated test-generation agent"
    model: "gpt-5-mini"

⸻⸻⸻

Follow Instruction Below :

    1. Analyze code.
    2. Generate tests.
    3. Run Maven + JaCoCo.
    4. Improve tests until coverage increases.


⸻⸻⸻

MCP Tools – Full API Documentation

Calculator Tools:

    add(a: float, b: float) -> float

    Adds two numbers.

sqrt(x: float) -> float:

    Computes square root.

⸻⸻⸻

Core Testing Agent Development (Phase 2)

    run_maven_tests(module: str) -> dict:

    Runs mvn test inside a module.
    Returns:
        • exit code
        • stdout/stderr
        • coverage percent

⸻⸻⸻

    suggest_tests(module: str) -> dict:

    Reads JaCoCo report → extracts uncovered methods → generates test templates.

    Returns:
        • list of uncovered methods
        • JUnit test templates

⸻⸻⸻

Git Automation Tools (Phase 3)

    git_status() -> dict:

    Returns:
        • modified files
        • untracked files
        • warnings/conflicts

⸻⸻⸻

git_add_all() -> dict:

    Stages all necessary files.

⸻⸻⸻

git_commit(message: str):

    Commits staged changes with standardized message.

⸻⸻⸻

git_push(remote: "origin", branch: "main"):

    Pushes to remote GitHub repository.

⸻⸻⸻

git_pull_request(base="main", title, body):

    Creates simulated PR metadata.

⸻⸻⸻

Intelligent Test Iteration (Phase 4)

    A custom script:

phase4_agent.py

    Performs:
        1. mvn test
        2. Parses JaCoCo XML
        3. Identifies uncovered methods
        4. Generates new tests
        5. Saves tests into: java_agent/src/test/java/generated/
        6. Re-runs tests
        7. Commits improvements to GitHub

    Bug fixing is included when tests expose failures.

⸻⸻⸻

Creative Extensions (Phase 5)

1. Specification-Based Testing Tool

    spec_based_tester(java_file: str):

    Performs:
        • boundary value analysis
        • equivalence partitioning
        • generates test cases

⸻⸻⸻

2. Code Review Agent

    code_review_agent(java_dir: str)

    Performs:
        • static analysis
        • code smell detection
        • style enforcement
        • basic security scanning
