import sys
from pathlib import Path

LOAD_ROOT = Path(__file__).resolve().parent
REPO_ROOT = LOAD_ROOT.parents[1]
for path in (LOAD_ROOT, REPO_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from tests.load.load_support.browser_flows import build_selected_e2e_flow_user_class  # noqa: E402

FrontendSelectedE2EFlowUser = build_selected_e2e_flow_user_class()
__all__ = ["FrontendSelectedE2EFlowUser"]
