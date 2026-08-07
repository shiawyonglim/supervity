with open('app/routers/data_manager.py', 'r') as f:
    code = f.read()

code = code.replace('c.lead_stage__c', 'c."Lead_Stage__c"')
code = code.replace('c.duplicate_key', 'c."duplicate_key"')
code = code.replace('c.confidence', 'c."confidence"')

with open('app/routers/data_manager.py', 'w') as f:
    f.write(code)
