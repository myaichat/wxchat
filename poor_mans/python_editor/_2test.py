import shelve
from datetime import datetime

# Open the shelve database
with shelve.open('counter.db') as db:
    # Try to read the count from the database
    try:
        count = db['count']
    except KeyError:
        # If the count doesn't exist, initialize it to 0
        count = 0

    # Increment the count
    count += 1

    # Write the updated count back to the database
    db['count'] = count

print(f'Executed _2test.py for the {count} time at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')