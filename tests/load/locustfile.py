import os

if os.getenv("TARANIS_LOAD_FLOWS"):
    from tests.load.load_support.browser_flows import build_selected_e2e_flow_user_class

    FrontendSelectedE2EFlowUser = build_selected_e2e_flow_user_class()
    __all__ = ["FrontendSelectedE2EFlowUser"]
else:
    from tests.load.load_support.browser_flows import FrontendBrowserUser

    __all__ = ["FrontendBrowserUser"]
