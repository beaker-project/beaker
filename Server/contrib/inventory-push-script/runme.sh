#!/bin/sh
inventory_server=https://inventory:insecure@inventory.engineering.redhat.com
system_name=$(hostname)

./pushInventory.py --server $inventory_server -h $system_name
./legacy-inventory.py --server $inventory_server -h $system_name

