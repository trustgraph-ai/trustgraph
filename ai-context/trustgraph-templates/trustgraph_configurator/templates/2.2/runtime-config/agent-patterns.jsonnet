
{
    "react": {
        "name": "react",
        "description": "Interleaved reasoning and action — the agent thinks, selects a tool, observes the result, and repeats until it has enough information to answer.",
        "max_iterations": 10,
    },
    "plan-then-execute": {
        "name": "plan-then-execute",
        "description": "The agent first produces a structured plan of steps, then executes each step in order. Supports re-planning on failure.",
        "max_iterations": 15,
        "max_replan_depth": 2,
    },
    "supervisor": {
        "name": "supervisor",
        "description": "The agent decomposes the question into independent sub-goals, fans out subagent requests, waits for all to complete, then synthesises a final answer.",
        "max_subagents": 5,
    },
}

