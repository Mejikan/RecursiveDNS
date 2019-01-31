# Lawrence Yong
# PROJ2 RS SERVER SCRIPT

import threading
import time
import random
import socket as sock
import sys

def localhostIP():
	return sock.gethostbyname(sock.gethostname()) # get local hostname

# Define TS COM and TS EDU hostnames
COM_hn = None # overrided by command line args if provided!
EDU_hn = None # overrided by command line args if provided!
# Define TLD Servers ports
COM_port = 3401
EDU_port = 3402
# Define the port to listen for incoming connections
port = 3400
# Define file to read from
in_filename = "PROJ2-DNSRS.txt" # overrided by command line args if provided!

############################### DNS STUFF ###############################

class Record:
	def __init__(self, input_str):
		split_str = input_str.strip().split()
		if (len(split_str) > 0):
			self.hostname = split_str[0]
		if (len(split_str) > 1):
			self.ip = split_str[1]
		if (len(split_str) > 2):
			if (split_str[2] == "A" or split_str[2] == "NS"):
				self.flag = split_str[2]
			else:
				raise ValueError("Unexpected DNS type: " + split_str[2])

	# serialize record to string
	def __str__(self):
		return "{} {} {}".format(self.hostname, self.ip, self.flag)
	
	# gets the top-level domain of this record's hostname
	def get_TLD(self):
		sep_i = self.hostname.rfind(".")
		if sep_i >= 0:
			return (self.hostname[sep_i+1:]).lower()
		else:
			raise Exception()

# takes a list of DNS string records and produces a table of record objects
def list_to_table(dns_list):
	DNS_table = {}
	for n in range(len(dns_list)):
		if len(dns_list[n].strip()) > 0:
			dns_rec = Record(dns_list[n])
			DNS_table[dns_rec.hostname] = dns_rec
	return DNS_table

# creates a DNS table from a properly formatted file
def read_table_from_file(filename):
	lines = []
	with open(filename) as in_file:
		lines = in_file.readlines()
	return list_to_table(lines)

############################### DNS STUFF ###############################

############################### SERVER STUFF ###############################

class Server:
	dnstype = ""

	def __init__(self, dnstype):
		self.dnstype = dnstype

	# logs a pre-formatted message
	def log(self, msg):
		print ("[" + self.dnstype + "]: " + msg)

	# starts the server with some port
	def start(self, port):
		try:
			ssocket = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
			self.ssocket = ssocket
		except sock.error as err:
			self.log("{0, 1} \n".format(self.dnstype + " server socket open error ", err))
		server_binding = ("", port) # using localhost
		ssocket.bind(server_binding)
		ssocket.listen(1)
		host = sock.gethostname() # resolve local hostname
		self.log("Server host name is: " + host)
		localhost_ip = (sock.gethostbyname(host))
		print("Server IP address is " + str(localhost_ip))
		csockid, addr = ssocket.accept() # accept client connection
		print ("Got a connection request from a client at " + str(addr))
		self.on_accept(csockid, addr)

		while (self.run()):
			pass
	
	# kills the server
	def kill(self):
		# Close the server socket
		self.ssocket.close() 
		exit()

	# the on_accept function is called when a new client connection is accepted
	# returns client socket id and address
	# the function is meant to be overriden by a subclass
	def on_accept(self, csock, addr):
		pass

	# the run function is called by the server continuously until it returns false
	# the function is meant to be overriden by a subclass
	def run(self):
		return False

############################### SERVER STUFF ###############################

class RServer(Server):
	# the table holding the dns records
	RS_table = {}
	# Define receive buffer size (bytes)
	msg_size = 256
	# Define string encoding scheme
	msg_encoding = "utf-8"
	# Define EOF, end-of-stream, signal: tells the server there are no more messages
	EOF_signal = "\r\n\r\n"

	# COM TLD sock
	comsock = None
	# EDU TLD sock
	edusock = None

	def __init__(self):
		super().__init__("RS")
	
	# connects to a remote host
	def connect(self, hostname, port):
		# open socket
		try:
			csock = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
		except sock.error as err:
			print("{0, 1} \n".format("socket open error ", err))

		# connect to the server
		server_binding = (hostname, port)
		csock.connect(server_binding)
		return csock
	
	# connects sockets to TLD servers
	def connectTLD(self, COM_hn, EDU_hn):
		if COM_hn is None:
			COM_rec = self.find_TLD_NS_entry("com")
			if not COM_rec:
				raise Exception("COM DNS record not found")
			COM_hn = COM_rec.ip
		if EDU_hn is None:
			EDU_rec = self.find_TLD_NS_entry("edu")
			if not EDU_rec:
				raise Exception("EDU DNS record not found")
			EDU_hn = EDU_rec.ip
		self.comsock = self.connect(COM_hn, COM_port)
		self.edusock = self.connect(EDU_hn, EDU_port)
		print("Connected to TLD servers.")
	
	def send_COM(self, msg):
		self.comsock.send(str(msg).encode(self.msg_encoding))

	def send_EDU(self, msg):
		self.edusock.send(str(msg).encode(self.msg_encoding))

	def recv_COM(self):
		return self.comsock.recv(self.msg_size).decode(self.msg_encoding)

	def recv_EDU(self):
		return self.edusock.recv(self.msg_size).decode(self.msg_encoding)
	
	def close_COM(self):
		self.send_COM(self.EOF_signal)
	
	def close_EDU(self):
		self.send_EDU(self.EOF_signal)

	def on_accept(self, csock, addr): # when client connection is accepted
		self.rcsock = csock

	def run(self): # continuously called
		msg = self.rcsock.recv(self.msg_size).decode(self.msg_encoding)
		# print("debug", msg) # debug
		if (msg == self.EOF_signal):
			self.rcsock.close()
			return False

		# look up hostname in dns records:
		hnstring = msg
		if hnstring in self.RS_table: # if match, reply with entry of format "Hostname IPaddress A"
			entry = self.RS_table[hnstring]
			self.rcsock.send(entry.__str__().encode(self.msg_encoding))
		else: # check appropriate TLD servers for DNS records (if applicable - has to be .edu or .com hostnames)
			if (hnstring[len(hnstring)-3:]).lower() == "edu": # edu TLD
				self.send_EDU(hnstring)
				edu_msg = self.recv_EDU()
				self.rcsock.send(edu_msg.encode(self.msg_encoding))
			elif (hnstring[len(hnstring)-3:]).lower() == "com": # com TLD
				self.send_COM(hnstring)
				com_msg = self.recv_COM()
				self.rcsock.send(com_msg.encode(self.msg_encoding))
			else:
				self.rcsock.send("{} - Error: HOST NOT FOUND".format(hnstring).encode(self.msg_encoding))
		return True

	def kill(self):
		# close TLD sockets
		self.comsock.close()
		self.edusock.close()
		self.ssocket.close()

	# finds one "NS" type DNS record
	def find_NS_entry(self):
		for key, val in self.RS_table.items():
			if val.flag == "NS":
				return val
		return None

	# finds a "NS" type DNS record with a matching TLD hostname
	def find_TLD_NS_entry(self, tld):
		for key, val in self.RS_table.items():
			if val.flag == "NS" and tld.lower() == val.get_TLD().lower():
				return val
		return None

# Read TS hostnames and filename from CLI args if provided
if (len(sys.argv) > 1):
	COM_hn = sys.argv[1]
if (len(sys.argv) > 2):
	EDU_hn = sys.argv[2]
if (len(sys.argv) > 3):
	in_filename = sys.argv[3]

rserv = RServer()
def run_rserver():
	# populate dns table
	rserv.RS_table.update(read_table_from_file(in_filename))

	try:
		rserv.connectTLD(COM_hn, EDU_hn)
		rserv.start(port)
	except Exception as e:
		raise e

t1 = threading.Thread(name='server', target=run_rserver)
t1.start()
time.sleep(random.random()*5)

input("Hit ENTER to exit\n")
rserv.kill()
time.sleep(random.random()*5)
exit()
