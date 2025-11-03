import subprocess
import time
import sys
from datetime import datetime

def run_script(script_name):
    print(f"\nRunning {script_name} at {datetime.now()}")
    try:
        result = subprocess.run([sys.executable, script_name], capture_output=True, text=True)
        print(f"Output from {script_name}:")
        print(result.stdout)
        if result.stderr:
            print(f"Errors from {script_name}:")
            print(result.stderr)
    except Exception as e:
        print(f"Error running {script_name}: {str(e)}")

# רשימת הסקריפטים לריצה
scripts = ['chatfon.py', 'appfon.py', 'send_chat']

while True:
    print(f"\nStarting new cycle at {datetime.now()}")
    
    for script in scripts:
        run_script(script)
        time.sleep(2)  # המתנה קצרה בין הסקריפטים
        
    print(f"Cycle completed at {datetime.now()}")
    print("Waiting for next cycle...")
    time.sleep(300)  # המתנה 5 דקות (300 שניות)