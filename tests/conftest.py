import os

# Prevent modal from failing when attempting to read ~/.modal.toml in restricted sandbox environments
if "MODAL_CONFIG_PATH" not in os.environ:
    os.environ["MODAL_CONFIG_PATH"] = os.path.abspath(".modal.dummy.toml")
