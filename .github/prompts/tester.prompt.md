---
agent: "agent"
tools: ['Test Agent/*']
description: "AI agent that iteratively improves test coverage based on JaCoCo results."
model: "gpt-5-mini"
---

## Instructions ##
1. Run `mvn test` in the connected Maven project.
2. Parse `target/site/jacoco/jacoco.xml` for uncovered methods.
3. Call `suggest_tests(module="java_agent")` to generate new JUnit tests.
4. Save generated test files under `src/test/java/generated/`.
5. Stage, commit, and push changes automatically.
6. Repeat until coverage improvement plateaus.