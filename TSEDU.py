# Lawrence Yong
# PROJ2 TLD SERVER SCRIPT

import threading
import time
import random
import socket as sock
import sys

# Define the type of TLD server (either COM or EDU) - this value is never actually used in order to keep things simple
tld_type = "EDU" # either COM or EDU

# Define the port to listen for incoming connections
port = 3402
# Define file to read from
in_filename = "PROJ2-DNSEDU.txt" # overrided by command line args if provided!

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

class TServer(Server):
	# the table holding the dns records
	TS_table = {}
	# Define receive buffer size (bytes)
	msg_size = 256
	# Define string encoding scheme
	msg_encoding = "utf-8"
	# Define EOF, end-of-stream, signal: tells the server there are no more messages
	EOF_signal = "\r\n\r\n"

	def __init__(self):
		super().__init__("TS")

	def on_accept(self, csock, addr): # when client connection is accepted
		self.tcsock = csock

	def run(self): # continuously called
		msg = self.tcsock.recv(self.msg_size).decode(self.msg_encoding)
		if (msg == self.EOF_signal):
			self.tcsock.close()
			return True
		
		# look up hostname in dns records:
		hnstring = msg		
		if hnstring in self.TS_table: # if match, reply with entry of format "Hostname IPaddress A"
			entry = self.TS_table[hnstring]
			self.tcsock.send(entry.__str__().encode(self.msg_encoding))
		else: 
			self.tcsock.send("{} - Error: HOST NOT FOUND".format(hnstring).encode(self.msg_encoding))
		return True

# Read filename from CLI args if provided
if (len(sys.argv) > 1):
	in_filename = sys.argv[1]

tserv = TServer()
def run_tserver():
	# populate dns table
	tserv.TS_table.update(read_table_from_file(in_filename))

	try:
		tserv.start(port)
	except Exception:
		pass

t1 = threading.Thread(name='server', target=run_tserver)
t1.start()
time.sleep(random.random()*5)

input("Hit ENTER to exit\n")
tserv.kill()
time.sleep(random.random()*5)
exit()