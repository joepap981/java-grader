import BaseHTTPServer
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
import threading

import json
import os
import subprocess
import re
import random
import time

import gc

port=1710
#Program.java = the name of the class that students are instructed to create

def randgen():
    return str(random.random()).split('.')[-1]+'_'+str('%.6f' % time.time()).split('.')[-1]

#handles http POST requests
class HTTPHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    def do_POST(self):
        body_len = int(self.headers.getheader('content-length', 0))
        body_content = self.rfile.read(body_len)
        problem_name, student_response = get_info(body_content)
        result = grade(problem_name, student_response)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(result)
       

#multithreaded server
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """ This class allows to handle requests in separated threads.
        No further content needed, don't touch this. """

def grade(problem_name, student_response):
    randfilename = randgen()
    program_name = "Program{0}_{1}".format(problem_name['problem_name'], randfilename)
    
    #create a new directory/java file with random name (to avoid conflicts)
    p = subprocess.Popen(["mkdir", program_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()


    source_file_location = "./"+program_name+"/Program.java"
    source_file = open(source_file_location, 'w')
    source_file.write(student_response)
    source_file.close()
    result = {}

    #compile newly created student response java file
    p = subprocess.Popen(["javac", source_file_location], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()

    if (err != ""):
        result.update({"compile_error": err})
        result = process_result(result)
        return result
    else:
        result.update({"compile_error": 0})

    test_runner = problem_name["problem_name"] + "TestRunner"
    test_runner_java = "/edx/java-grader/" + test_runner + ".java"

    #copy the testrunner file to the newly created folder
    p = subprocess.Popen(["cp",test_runner_java, program_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()

    p = subprocess.Popen(["javac", "-d", program_name, "-classpath", "./"+program_name+":./junit-4.11.jar:./hamcrest-core-1.3.jar",test_runner_java], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()

    print "compile"
    print "out: "+out
    print "err: "+err


    p = subprocess.Popen(["java", "-classpath", "./"+program_name+":/edx/java-grader/junit-4.11.jar:/edx/java-grader/hamcrest-core-1.3.jar", test_runner], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()

    print "run java"
    print "out: "+out
    print "err: "+err


    out = re.split('\n', out)
    correct = out[len(out) - 2]


    if (correct == "true"):
        correct = True
	message = "Good job!"
    else:
        correct = False
	message = err+"\n"+out[0]

    result.update({"correct": correct, "msg": message,})
    result = process_result(result)

    #remove the newly created directory containing student response java file + test class
    p = subprocess.Popen(["rm","-rf", program_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()

    p = subprocess.Popen(["rm", test_runner], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()

    return result

def process_result(result):

    if (result["compile_error"] != 0):
        correct = False
        score = 0
        message = result["compile_error"]
    else:
        correct = result["correct"]
        message = result["msg"]

    if (correct == True):
        score = 1
    else:
        score = 0

    result = {}
    result.update({"correct": correct, "score": score, "msg": message })
    result = json.dumps(result)
    return result

def get_info(body_content):
    json_object = json.loads(body_content)
    json_object = json.loads(json_object["xqueue_body"])
    problem_name = json.loads(json_object["grader_payload"])
    student_response = json_object["student_response"]
    return problem_name, student_response

if __name__ == "__main__":

    server = ThreadedHTTPServer(("localhost", port), HTTPHandler)
    print "The Grader server is running on port "+str(port)+"..."
    print "Keep this server running for continued external grader service."
    server.serve_forever()
