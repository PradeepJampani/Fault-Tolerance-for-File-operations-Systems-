#!/usr/bin/env python
import logging
from collections import defaultdict
from errno import ENOENT
from stat import S_IFDIR, S_IFLNK, S_IFREG
from sys import argv, exit
from time import time
from time import time
import datetime
from fuse import FUSE, FuseOSError, Operations, LoggingMixIn
from xmlrpclib import Binary
import sys, pickle, xmlrpclib
from socket import error as socket_error

serverstatus = []
# status is = 0 when starting
# status is = 1 when server has shut down or connection error
# status is = 2 when data is corrupted

url_meta = "http:"
url_list=[]
count = 0
qr = 0
qw = 0
reads = 0
writes = 0

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

if not hasattr(__builtins__, 'bytes'):
    bytes = str

def refresh (corr_index,wrong_index):
    try :
        print "inside the refresh function"
        rpc = xmlrpclib.Server(url_list[wrong_index])
        ret = rpc.load_data(url_list[corr_index])
        if ret == 1:
            #setting the status back to normal
            serverstatus[wrong_index]=0
            return 1
        else :
            return 0
            #serverstatus[wrong_index] stays the same
    except socket_error as serr :
        print "connection error server "+url_list[wrong_index]+"restarting"
        serverstatus[wrong_index]=1

class FileNode:
    def __init__(self,name,isFile,path,url):
        self.name = name
        self.path = path
        self.url = url
        self.isFile = isFile # true if node is a file, false if is a directory.
        self.put("data","") # used if it is a file
        self.put("meta",{})
        self.put("list_nodes",{})# contains a tuple of <name:FileNode>  used only if it is a dir. 

    def put(self,key,value):
        if key == "meta" or key == "list_nodes":
            key = self.path+"&&"+key
            rpc = xmlrpclib.Server(url_meta)
            rpc.put(Binary(key), Binary(pickle.dumps(value)), 6000)
        else :
            key = self.path+"&&"+key
            #for injecting wrong value inside the server "http://localhost:51235"
            url_wrong = "http://localhost:51235/"
            value_wrong = {20:30, 30:40}
            #print "value", value
            #print "value_wrong", value_wrong
            
            for x in xrange(0, (len(url_list))):
                try :
                    if (serverstatus[x] != 0):
                        print serverstatus
                        corr_index = serverstatus.index(0)
                        wrong_index = x
                        ret = refresh(corr_index, wrong_index)
                    rpc = xmlrpclib.Server(url_list[x])
                    rpc.put(Binary(key),Binary(pickle.dumps(value)),6000)
                    #print "after put"
                    res = rpc.get(Binary(key))
                    #print "res" ,pickle.loads(res["value"].data)
                except socket_error as serr :
                    print "connection error server at"+url_list[x]+"restarting"
                    #becuase the server has stopped we are giving it to the status 1
                    serverstatus[x]=1
                    print serverstatus
            #rpc = xmlrpclib.Server(url_wrong)
            #rpc.put(Binary(key), Binary(pickle.dumps(value_wrong)),6000)
            #res = rpc.get(Binary(key))
            #print "wrong value",pickle.loads(res["value"].data)

    def get(self,key):
        res_get = []
        if key == "meta" or key == "list_nodes":
            #print "getting from the meta server"
            key = self.path+"&&"+key
            rpc = xmlrpclib.Server(url_meta)
            res = rpc.get(Binary(key))
            if "value" in res:
                #print pickle.loads(res["value"].data)
                return pickle.loads(res["value"].data)
            else:
                return None
        else :
            key = self.path+"&&"+key
            #print "getting from the data server"
            #print "reads", reads, " writes",writes
            # for x in xrange(0, (len(url_list))):
            #     rpc = xmlrpclib.Server(url_list[x])
            #     res = (rpc.get(Binary(key)))
            #     append_value = pickle.loads(res["value"].data)
            #     print "append_value",append_value
            #     res_get.append(append_value)
            res = self.vote (key)
            if "value" in res:
                #print pickle.loads(res["value"].data)
                return pickle.loads(res["value"].data)
            else :
                return None

    def vote(self,key):
        flag = 0
        #result_new = res_get
        x = 0
        while flag ==0 and x <= (len(url_list)-1):
            correctlist = list()
            correct = 0
            wrong =0
            for i in xrange(0,(len(url_list))):
                #print "checking ", url_list[x],"\n with ",url_list[i]
                #get data from server x
                if (serverstatus[x] !=0):
                    corr_index = serverstatus.index(0)
                    wrong_index = x
                    refresh(corr_index, wrong_index)
                if (serverstatus[i] != 0):
                    corr_index = serverstatus.index(0)
                    wrong_index = i
                    refresh(corr_index,wrong_index)
                try :
                    rpc1 = xmlrpclib.Server(url_list[x])
                    res1 = rpc1.get(Binary(key))
                    result1 = pickle.loads(res1["value"].data)
                except socket_error as serr :
                    print "connection error in server, ",url_list[x]
                    serverstatus[x]=1
                    print serverstatus
                except Exception as e:
                    serverstatus[i] = 1
                    print  serverstatus

                #get data from server i
                try:
                    rpc2 = xmlrpclib.Server(url_list[i])
                    res2 = rpc2.get(Binary(key))
                    result2 = pickle.loads(res2["value"].data)
                except socket_error as serr :
                    print "connection error in ",url_list[i]
                    serverstatus[i] = 1
                    print serverstatus
                except Exception as e :
                    serverstatus[i] = 1
                    print serverstatus
                #print "checking ", result1 ,"\n with ",result2 
                if result1 == result2:
                    print "correct"
                    correctlist.append("correct")
                else :
                    print "wrong"
                    correctlist.append("wrong")
                    #this means the data is wrong here or the data is corrupted. Status changed to 2
            
            for k in xrange(0,len(correctlist)):
                if correctlist[k]=="correct" :
                    correct = correct+1
                else :
                    wrong = wrong +1
            print "correct ",correct ," wrong ", wrong

            if correct >= int(qr) : #correct is greater than wrong
                print "\ncorrect > wrong/Qr"
                for k in xrange(0,len(correctlist)):
                    if correctlist[k]=="wrong" :
                        serverstatus[k]=2
                print serverstatus
                return res1
            else :
                if wrong >= int(qr):
                    serverstatus[x] = 2
                    print serverstatus
                x=x+1
        print "going to return none in Vote function"
        return None
    
    def set_data(self,data_blob):
        self.put("data",data_blob)
        

    def set_meta(self,meta):
        self.put("meta",meta)

    def get_data(self):
        return self.get("data")

    def get_meta(self):
        return self.get("meta")

    def list_nodes(self):
        return self.get("list_nodes").values()

    def add_node(self,newnode):
        list_nodes = self.get("list_nodes")
        list_nodes[newnode.name]=newnode
        self.put("list_nodes",list_nodes)

    def contains_node(self,name): # returns node object if it exists
        if (self.isFile==True):
            return None
        else:
            if name in self.get("list_nodes").keys():
                return self.get("list_nodes")[name]
            else:
                return None


class FS:
    def __init__(self,url):
        self.url = url
        self.root = FileNode('/',False,'/',url)
        now = time()
        self.fd = 0
        self.root.set_meta(dict(st_mode=(S_IFDIR | 0755), st_ctime=now,st_mtime=now,\
                                         st_atime=now, st_nlink=2))
    # returns the desired FileNode object
    def get_node_wrapper(self,path): # pathname of the file being probed.
        # Handle special case for root node
        if path == '/':
            return self.root
        PATH = path.split('/') # break pathname into a list of components
        name = PATH[-1]
        PATH[0]='/' # splitting of a '/' leading string yields "" in first slot.
        return self.get_node(self.root,PATH,name) 


    def get_node(self,parent,PATH,name):
        next_node = parent.contains_node(PATH[1])
        if (next_node == None or next_node.name == name):
            return next_node
        else:
            return self.get_node(next_node,PATH[1:],name)

    def get_parent_node(self,path):
        parent_path = "/"+("/".join(path.split('/')[1:-1]))
        parent_node = self.get_node_wrapper(parent_path)
        return parent_node

    def add_node(self,node,path):
        parent_path = "/"+("/".join(path.split('/')[1:-1]))
        parent_node = self.get_node_wrapper(parent_path)
        parent_node.add_node(node)
        if (not node.isFile):
            meta = parent_node.get("meta")
            meta['st_nlink']+=1
            parent_node.put("meta",meta)
        else:
            self.fd+=1
            return self.fd

    def add_dir(self,path,mode):
        # create a file node
        temp_node = FileNode(path.split('/')[-1],False,path,self.url)
        temp_node.set_meta(dict(st_mode=(S_IFDIR | mode), st_nlink=2,
                                st_size=0, st_ctime=time(), st_mtime=time(),
                                st_atime=time()))
        # Add node to the FS
        self.add_node(temp_node,path)
  

    def add_file(self,path,mode):
        # create a file node
        temp_node = FileNode(path.split('/')[-1],True,path,self.url)
        temp_node.set_meta(dict(st_mode=(S_IFREG | mode), st_nlink=1,
        st_size=0, st_ctime=time(), st_mtime=time(),
        st_atime=time()))
        # Add node to the FS
        # before we do that, we have to manipulate the path string to point
        self.add_node(temp_node,path)
        self.fd+=1
        return self.fd

    def write_file(self,path,data=None, offset=0, fh=None):
        # file will already have been created before this call
        # get the corresponding file node
        filenode = self.get_node_wrapper(path)
        # if data == None, this is just a truncate request,using offset as 
        # truncation parameter equivalent to length
        node_data = filenode.get("data")
        node_meta = filenode.get("meta")
        if (data==None):
            node_data = node_data[:offset]
            node_meta['st_size'] = offset
        else:
            node_data = node_data[:offset]+data
            node_meta['st_size'] = len(node_data)
        filenode.put("data",node_data)
        filenode.put("meta",node_meta)
        

    def read_file(self,path,offset=0,size=None):
        # get file node
        filenode = self.get_node_wrapper(path)
        # if size==None, this is a readLink request
        if (size==None):
            return filenode.get_data()
        else:
            # return requested portion data
            return filenode.get("data")[offset:offset + size]

    def rename_node(self,old,new):
        # first check if parent exists i.e. destination path is valid
        future_parent_node = self.get_parent_node(new)
        if (future_parent_node == None):
            raise  FuseOSError(ENOENT)
            return
        # get old filenodeobject and its parent filenode object
        filenode = self.get_node_wrapper(old)
        parent_filenode = self.get_parent_node(old)
        # remove node from parent
        list_nodes = parent_filenode.get("list_nodes")
        del list_nodes[filenode.name]
        parent_filenode.put("list_nodes",list_nodes)
        # if filenode is a directory decrement 'st_link' of parent
        if (not filenode.isFile):
            parent_meta = parent_filenode.get("meta")
            parent_meta["st_nlink"]-=1
            parent_filenode.put("meta",parent_meta)
        # add filenode to new parent, also change the name
        filenode.name = new.split('/')[-1]
        future_parent_node.add_node(filenode)

    def utimens(self,path,times):
        filenode = self.get_node_wrapper(path)
        now = time()
        atime, mtime = times if times else (now, now)
        meta = filenode.get("meta")
        meta['st_atime'] = atime
        meta['st_mtime'] = mtime
        filenode.put("meta",meta)


    def delete_node(self,path):
        # get parent node
        parent_filenode = self.get_parent_node(path)
        # get node to be deleted
        filenode = self.get_node_wrapper(path)
        # remove node from parents list
        list_nodes = parent_filenode.get("list_nodes")
        del list_nodes[filenode.name]
        parent_filenode.put("list_nodes",list_nodes)
        # if its a dir reduce 'st_nlink' in parent
        if (not filenode.isFile):
            parents_meta = parent_filenode.get("meta")
            parents_meta["st_nlink"]-=1
            parent_filenode.put("meta",parents_meta)

    def link_nodes(self,target,source):
        # create a new target node.
        temp_node = FileNode(target.split('/')[-1],True,target,self.url)
        temp_node.set_meta(dict(st_mode=(S_IFLNK | 0777), st_nlink=1,
                                  st_size=len(source)))
        temp_node.set_data(source)
        # add the new node to FS
        self.add_node(temp_node,target)

    def update_meta(self,path,mode=None,uid=None,gid=None):
        # get the desired filenode.
        filenode = self.get_node_wrapper(path)
        # if chmod request
        meta = filenode.get("meta")
        if (uid==None):
            meta["st_mode"] &= 0770000
            meta["st_mode"] |= mode
        else: # a chown request
            meta['st_uid'] = uid
            meta['st_gid'] = gid
        filenode.put("meta",meta)

class Memory(LoggingMixIn, Operations):
    'Example memory filesystem. Supports only one level of files.'

    def __init__(self,url):
        global count # count is a global variable, can be used inside any function.
        count +=1 # increment count for very method call, to track count of calls made.
        print ("CallCount {} " " Time {}".format(count,datetime.datetime.now().time())) # print the parameters passed to the method as input.(used for debugging)
        print('In function __init__()') #print name of the method called

        self.FS = FS(url)
       
        
       
        
    def getattr(self, path, fh=None):
        global count
        count +=1
        print ("CallCount {} " " Time {} arguments:{} {} {}".format(count,datetime.datetime.now().time(),type(self),path,type(fh)))
        print('In function getattr()')
        
        file_node =  self.FS.get_node_wrapper(path)
        if (file_node == None):
            raise FuseOSError(ENOENT)
        else:
            return file_node.get_meta()


    def readdir(self, path, fh):
        global count
        count +=1
        print ("CallCount {} " " Time {}".format(count,datetime.datetime.now().time()))
        print('In function readdir()')

        file_node =  self.FS.get_node_wrapper(path)
        m = ['.','..']+[x.name for x in file_node.list_nodes()]
        print m
        return m

    def mkdir(self, path, mode):
        global count
        count +=1
        print ("CallCount {} " " Time {}" "," "argumnets:" " " "path;{}" "," "mode:{}".format(count,datetime.datetime.now().time(),path,mode))
        print('In function mkdir()')       
        # create a file node
        self.FS.add_dir(path,mode)

    def create(self, path, mode):
        global count
        count +=1
        print ("CallCount {} " " Time {} path {} mode {}".format(count,datetime.datetime.now().time(),path,mode))
        print('In function create()')
        
        return self.FS.add_file(path,mode) # returns incremented fd.

    def write(self, path, data, offset, fh):
        global count
        count +=1
        print ("CallCount {} " " Time {}".format(count,datetime.datetime.now().time()))
        print ("Path:{}" " " "data:{}" " " "offset:{}" " "  "filehandle{}".format(path,data,offset,fh))
        print('In function write()')
        
        self.FS.write_file(path, data, offset, fh)
        return len(data)

    def open(self, path, flags):
        global count
        count +=1
        print ("CallCount {} " " Time {}" " " "argumnets:" " " "path:{}" "," "flags:{}".format(count,datetime.datetime.now().time(),path,flags))
        print('In function open()')

        self.FS.fd += 1
        return  self.FS.fd 

    def read(self, path, size, offset, fh):
        global count
        count +=1
        print ("CallCount {} " " Time {}" " " "arguments:" " " "path:{}" "," "size:{}" "," "offset:{}" "," "fh:{}".format(count,datetime.datetime.now().time(),path,size,offset,fh))
        print('In function read()')

        return self.FS.read_file(path,offset,size)

    def rename(self, old, new):
        global count
        count +=1
        print ("CallCount {} " " Time {}".format(count,datetime.datetime.now().time()))
        print('In function rename()')

        self.FS.rename_node(old,new)

    def utimens(self, path, times=None):
        global count
        count +=1
        print ("CallCount {} " " Time {} Path {}".format(count,datetime.datetime.now().time(),path))
        print('In function utimens()')

        self.FS.utimens(path,times)

    def rmdir(self, path):
        global count
        count +=1
        print ("CallCount {} " " Time {}".format(count,datetime.datetime.now().time()))
        print('In function rmdir()')

        self.FS.delete_node(path)

    def unlink(self, path):
        global count
        count +=1
        print ("CallCount {} " " Time {}".format(count,datetime.datetime.now().time()))
        print('In function unlink()')

        self.FS.delete_node(path)

    def symlink(self, target, source):
        global count
        count +=1
        print ("CallCount {} " " Time {}" "," "Target:{}" "," "Source:{}".format(count,datetime.datetime.now().time(),target,source))
        print('In function symlink()')

        self.FS.link_nodes(target,source)

    def readlink(self, path):
        global count
        count +=1
        print ("CallCount {} " " Time {}".format(count,datetime.datetime.now().time()))
        print('In function readlink()')
        
        return self.FS.read_file(path)

    def truncate(self, path, length, fh=None):
        global count
        print ("CallCount {} " " Time {}""," "arguments:" "path:{}" "," "length:{}" "," "fh:{}".format(count,datetime.datetime.now().time(),path,length,fh))
        print('In function truncate()')
        
        self.FS.write_file(path,offset=length)

    def chmod(self, path, mode):
        global count
        count +=1
        print ("CallCount {} " " Time {}".format(count,datetime.datetime.now().time()))
        print('In function chmod()')

        self.FS.update_meta(path,mode=mode)
        return 0

    def chown(self, path, uid, gid):
        global count
        count +=1
        print ("CallCount {} " " Time {}".format(count,datetime.datetime.now().time()))
        print('In function chown()')

        self.FS.update_meta(path,uid=uid,gid=gid)
        
        
   
if __name__ == "__main__":
  if len(argv) <= 3:
    print 'usage: %s <mountpoint> <meta hashtable> <Qr> <Qw> <data server1> <data server2>.... <data server n>' % argv[0]
    exit(1)
  #print "Qr",argv[3],"Qw",argv[4]
  qr = argv[3]
  qw = argv[4]
  #print "Qr",qr,"Qw",qw
  append_value = "http://localhost:"+argv[2]+"/"
  url_meta = append_value
  for i in xrange(5,len(argv)):
    apnd_val = "http://localhost:"+argv[i]+"/"
    #print "apnd_val...", apnd_val 
    url_list.append(apnd_val)
  if qr < 3:
    print "the corrupt data will not be corrected if Qr is lesser than 3"
  if qr < int(qw):
    print "Qr should be greater than ",(len(url_list)/2)
    exit(1)
  if int(qw) != len(url_list):
    print "the Qw should be equal to the number of servers"
    print len(url_list)
    print qw
    exit (1)
  #initialise all the servers at state 0
  for i in xrange (0 , len(url_list)):
    serverstatus.append(0)
  print serverstatus
  # Create a new HtProxy object using the URL specified at the command-line
  print url_list
  fuse = FUSE(Memory(url_list[0]), argv[1], foreground=True)
