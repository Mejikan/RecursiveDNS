# Lawrence Yong
# PROJ2 CLIENT SCRIPT

import socket as sock
import sys

def localhostIP():
	return sock.gethostbyname(sock.gethostname()) # get local hostname

# Define RS hostname, port
rs_hn = localhostIP() # overrided by command line args if provided!
rs_port = 3400
# Define file to read from
in_filename = "PROJ2-HNS.txt" # overrided by command line args if provided!
# Define file to write to
out_filename = "RESOLVED.txt"

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

class Client:
	# Define receive buffer size (bytes)
	msg_size = 256
	# Define string encoding scheme
	msg_encoding = "utf-8"
	# Define EOF, end-of-stream, signal: tells the server there are no more messages
	EOF_signal = "\r\n\r\n"

	# construct Client instance (file is the file to write results to)
	def __init__(self, ofile):
		self.out_file = ofile

	# logs a pre-formatted message
	def log(self, msg):
		print ("[C]: " + msg)

	# outputs a message to a destination (file, console, etc)
	def output(self, msg):
		self.log(msg)
		self.out_file.write(msg + "\n")

	# connects to a server
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

	def connect_RS(self, hostname, port):
		self.ctors = self.connect(hostname, port)

	def send_RS(self, msg):
		self.ctors.send(str(msg).encode(self.msg_encoding))

	def recv_RS(self):
		return self.ctors.recv(self.msg_size).decode(self.msg_encoding)
	
	def close_RS(self):
		self.send_RS(self.EOF_signal)

	# contacts DNS servers to resolve a hostname
	def resolve_DNS(self, hostname):
		self.send_RS(hostname)
		rs_msg = self.recv_RS()
		try:
			rs_dns_rec = Record(rs_msg)
			if (rs_dns_rec.flag == "A"):
				self.output(rs_dns_rec.__str__())
		except:
			self.output(rs_msg)

def run_client():
	out_file = open(out_filename, "w")

	# construct client and connect to RS server
	client = Client(out_file)
	client.connect_RS(rs_hn, rs_port)

	# read in hostnames and resolve them
	queries = []
	with open(in_filename) as in_file:
		queries = in_file.readlines()

	for q in range(len(queries)):
		client.resolve_DNS(queries[q].strip())

	# close connections
	client.close_RS()

	out_file.close()

# Read RS hostname and filename from CLI args if provided
if (len(sys.argv) > 1):
	rs_hn = sys.argv[1]
if (len(sys.argv) > 2):
	in_filename = sys.argv[2]

run_client()
