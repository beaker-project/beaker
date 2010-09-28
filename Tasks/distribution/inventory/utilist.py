#! /usr/bin/python
# -*- python -*-
# -*- coding: utf-8 -*-

def hexbitmask(l, nr_entries):
	hexbitmask = []
	bit = 0
	mask = 0
	for entry in range(nr_entries):
		if entry in l:
			mask |= (1 << bit)
		bit += 1
		if bit == 32:
			bit = 0
			hexbitmask.insert(0, mask)
			mask = 0

	if bit < 32 and mask != 0:
		hexbitmask.insert(0, mask)

	return hexbitmask

def bitmasklist(line, nr_entries):
	fields = line.strip().split(",")
	bitmasklist = []
	entry = 0
	for i in range(len(fields) - 1, -1, -1):
		mask = int(fields[i], 16)
		while mask != 0:
			if mask & 1:
				bitmasklist.append(entry)
			mask >>= 1
			entry += 1
			if entry == nr_entries:
				break
		if entry == nr_entries:
			break
	return bitmasklist
