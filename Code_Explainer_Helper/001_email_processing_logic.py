import sys
sys.path.insert(0, 'src')
from jobs import email_check

# Show the main processing flow
print("=== EMAIL CHECK PROCESS ===")
print("1. PROVIDERS:", email_check.PROVIDERS.keys())
print("2. STATE FILE:", email_check.STATE_FILE)
print("3. CONFIG DIR:", email_check.CONFIG_DIR)

# Show the main function structure
import inspect
main_source = inspect.getsource(email_check.main)
print("\n=== MAIN FUNCTION LOGIC ===")
print(main_source[:1500] + "...")