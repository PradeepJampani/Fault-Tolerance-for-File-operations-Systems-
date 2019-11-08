#!/usr/bin/env python
import sys, os
from sys import argv, exit
import time

def launch_servers(port_id):
    cmd = ['xterm', '-e', 'python' , 'metaserver.py', '--port=%s' % port_id]
    os.execvp('xterm', cmd)

if __name__ == '__main__':
    if len(argv) < 1:
        print( "usage: python dataserver.py <port for local instance> <port for data-server2> ..<port for data-server-n>")
        sys.exit(1)
    server_Ids = []
    for id in range(len(argv) -1 ):
        print id
        server_Ids.append(argv[id+1])
    print server_Ids
    for servers in server_Ids:	
		pid = os.fork()
		if pid == 0:
             		if pid == 0:
               			launch_servers(servers)
    	   		break
