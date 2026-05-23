import sys
import os

# Ensure the project root is on sys.path so that services/, models/, etc.
# can be imported with absolute names (e.g. "from services.user_service import ...").
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
