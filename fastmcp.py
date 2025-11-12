# Minimal stub of FastMCP used for local testing
class FastMCP:
    def __init__(self, name=None):
        self.name = name

    def tool(self):
        # decorator that returns the function unchanged
        def decorator(f):
            return f
        return decorator

    def run(self, transport=None):
        # no-op for local testing
        pass
