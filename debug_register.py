import time
import registration

print('Calling start_registration...')
result = registration.start_registration('debug_user')
print('start_registration returned:', result)
# Wait to let the background thread run and print messages
for i in range(10):
    prog = registration.get_progress()
    print('progress:', prog)
    time.sleep(1)
print('Done')
