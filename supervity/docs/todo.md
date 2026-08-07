flow

1. python will read and clean the data
2. create a loop for all different prospect id
3. sends the data to supervity (email, user
   a. read the data sent by supervity (ask for user input using slack if there is missing values)
   b. score the user their intent
   c. Check privacy law
   d. draft and send email
   e. report summary (tell the user through slack for what the ai have done)
   what needs to be done
4. integrate the llm (done)
   a. add nvidian nim for the the brain
   b. use gemini for the json related
5. seed the data (done)
6. build the 5 operators (done)
7. set up the settings
8. fix the search button
9. upload data to the database
10. connect front end and backend (done)
11. fix the main dashboard (done)
    a. tell the user about the finished things
12. setup ai manager (basically the orchestrator)
    a. The Instructions
13. setup workbench (for handling error) --wait
    a. ai assistant
    b. automation builder
    c. quick actions
14. ai policies (add rules for the ai)
    a. research what does ai policy do( because I still don’t really understand, like does the system based on the ai policy have here or do I need to sync the ai policy inside supervity)
    b. ai policies only have front end only does not have back end
    c. add backend
    d. policies
    e. create with ai
    f. structured builder
    g. permission matrix
15. ai insight (display what the ai is thinking)
    a. still need a lot of double checking (a lot of button do not work and a lot of them dunno where to map to)
    b. Backend Analyzer
    c. The Dashboard
16. data manager (handle clean and organize messy data)
    a. Buying Group Resolution
    b. Deduplication Rules
    c. Routing Configuration
    d. Data analyser
    e. Data aquality
    i. Later need to add an ai to tell the user what to do if they encounter this issue, why this issue happens and more
17. Wow factors
    a. Self-learning
    b. Revenue forecasting
    i. analyzes the Opportunity and VisitorActivity tables. It calculates your current win rate and predicts
    c. deep auditability
    i. show how the ai thinks step by step
    d. collision detection
    i. detect is the person in the same company is already talking ot one of our sales rep
    e. automation
    i. Write a backend prompt that analyzes your Workbench exceptions. Have the AI Insight tab pop up a recommendation saying: "Human operators manually merged 'IBM' and 'Intl Business Machines' 4 times today. Would you like me to create an AI Policy to auto-merge these in the future?" Clicking "Yes" automatically writes the policy.
