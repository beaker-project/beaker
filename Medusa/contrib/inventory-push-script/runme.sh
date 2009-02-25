#!/bin/sh
inventory_user=inventory
inventory_password=insecure 
inventory_server=inventory.engineering.redhat.com
system_name=$(hostname)

./pushInventory.py --user $inventory_user --password $inventory_password --server $inventory_server -h $system_name
./legacy-inventory.py --user $inventory_user --password $inventory_password --server $inventory_server -h $system_name

