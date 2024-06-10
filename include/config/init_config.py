from include.config.AppConfig import AppConfig

# Initialize the AppConfig instance or any other relevant configuration here
apc = AppConfig()

# You might have an initialization function like this
def init(**kwargs):
    global apc
    # Initialize apc with necessary parameters
    apc.init(**kwargs)
    # Additional setup if needed