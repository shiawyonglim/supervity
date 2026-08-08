import os
import json
import requests
import time

# --- CONFIGURATION ---
# Set your API key here or in your .env / environment variables
API_KEY = os.getenv("WORKFLOW_API_KEY", "<your-api-key>")
WORKFLOW_ID = "019fdfc8-5bf8-7000-8708-31436f168d55"
URL = "https://auto-workflow-api.supervity.ai/api/v1/workflow-runs/execute/stream"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "x-source": "external",
    "x-active-org": "R.E.P.O",
    "x-user-timezone": "Asia/Kuala_Lumpur"
}

# --- TEST DATASET ---
TEST_CASES = [
  {
    "scenario": "Test 1: Privacy Compliance Blocked",
    "payload": {
      "prospect_id": "P-1001",
      "sender_id": "S-001",
      "contact": {
        "name": "Jane Doe",
        "email": "jane.doe@acme-eu.com",
        "title": "VP of Engineering",
        "region": "EU",
        "explicit_consent": False,
        "lead_stage__c": "Open"
      },
      "account": {
        "name": "Acme EU",
        "industry": "Manufacturing",
        "employees": "1000-5000"
      }
    }
  },
  {
    "scenario": "Test 2: Normal Fast Routing (MQL)",
    "payload": {
      "prospect_id": "P-1002",
      "sender_id": "S-002",
      "contact": {
        "name": "John Smith",
        "email": "john.smith@betacorp.com",
        "title": "Director of IT",
        "region": "NA",
        "explicit_consent": True,
        "lead_stage__c": "MQL"
      },
      "account": {
        "name": "Beta Corp",
        "industry": "Technology",
        "employees": "500-1000"
      }
    }
  },
  {
    "scenario": "Test 3: Normal Fast Routing (Opportunity)",
    "payload": {
      "prospect_id": "P-1003",
      "sender_id": "S-001",
      "contact": {
        "name": "Alice Wong",
        "email": "awong@gammainc.io",
        "title": "Chief Information Officer",
        "region": "APAC",
        "explicit_consent": True,
        "lead_stage__c": "Opportunity"
      },
      "account": {
        "name": "Gamma Inc",
        "industry": "Finance",
        "employees": "5000+"
      }
    }
  },
  {
    "scenario": "Test 4: Human Workbench Collision (SQL)",
    "payload": {
      "prospect_id": "P-1004",
      "sender_id": "S-003",
      "contact": {
        "name": "Bob Miller",
        "email": "bmiller@deltallc.net",
        "title": "Head of Operations",
        "region": "NA",
        "explicit_consent": True,
        "lead_stage__c": "SQL"
      },
      "account": {
        "name": "Delta LLC",
        "industry": "Retail",
        "employees": "200-500"
      }
    }
  },
  {
    "scenario": "Test 5: System Error Halt (Missing/Invalid Stage)",
    "payload": {
      "prospect_id": "P-1005",
      "sender_id": "S-002",
      "contact": {
        "name": "Eve Davis",
        "email": "eve.davis@epsilongroup.co.uk",
        "title": "Marketing Manager",
        "region": "EMEA",
        "explicit_consent": True,
        "lead_stage__c": None
      },
      "account": {
        "name": "Epsilon Group",
        "industry": "Media",
        "employees": "50-200"
      }
    }
  }
]

def run_tests():
    print(f"Starting Supervity Workflow Tests. API Key provided: {'Yes' if API_KEY != '<your-api-key>' else 'No - Using Dummy Key'}")
    print("-" * 50)
    
    for i, test in enumerate(TEST_CASES, 1):
        print(f"Running [{i}/{len(TEST_CASES)}]: {test['scenario']}")
        
        # Supervity expects multipart/form-data where the JSON payload is a string inside the form
        payload_str = json.dumps(test["payload"])
        
        files = {
            "workflowId": (None, WORKFLOW_ID),
            "inputs[lead_payload]": (None, payload_str)
        }
        
        try:
            response = requests.post(URL, headers=HEADERS, files=files)
            
            print(f"  Status Code: {response.status_code}")
            if response.status_code == 200:
                print("  Result: SUCCESS")
                # print(f"  Response: {response.text}") # Uncomment to see full response
            else:
                print(f"  Result: FAILED - {response.text}")
                
        except Exception as e:
            print(f"  Error triggering webhook: {e}")
            
        print("-" * 50)
        
        # Sleep for a moment between requests to avoid rate limits
        time.sleep(2)
        
    print("Test run complete!")

if __name__ == "__main__":
    run_tests()
