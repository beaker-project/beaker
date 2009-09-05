
# Client code

import xmlrpclib

# Connect to lab controller via unauth xmlrpc
server = xmlrpclib.Server('http://localhost:8000', allow_none=True)

# Ask for host hp-lp1.example.com xml file..
print server.get_recipe('hp-lp1.example.com')

# Ask for my xml file.  This will return whatever my active recipe is 
print server.get_recipe()

# Start task_id 127 with no kill_time override
print server.task_start(127, None)

# Stop task id 127 
print server.task_stop(127,'Stop',None)
