with open('app/routers/data_manager.py', 'r') as f:
    lines = f.readlines()

with open('app/routers/quality_temp.py', 'r') as f:
    new_logic = f.read()

start_idx = -1
for i, line in enumerate(lines):
    if '@router.get("/quality")' in line:
        start_idx = i
        break

if start_idx != -1:
    new_lines = lines[:start_idx]
    with open('app/routers/data_manager.py', 'w') as f:
        f.writelines(new_lines)
        f.write(new_logic)
        f.write('\n')
    print('Successfully replaced data_quality logic.')
else:
    print('Could not find /quality route.')
