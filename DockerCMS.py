from flask import Flask, Response, render_template, request
import json
from subprocess import Popen, PIPE
import os
from tempfile import mkdtemp
from werkzeug import secure_filename
app = Flask(__name__)

@app.route("/")
def index():
    return """
Available API endpoints:

GET /containers                     List all containers
GET /containers?state=running       List running containers (only)
GET /containers/<id>                Inspect a specific container
GET /containers/<id>/logs           Dump specific container logs
GET /images                         List all images


POST /images                        Create a new image
POST /containers                    Create a new container

PATCH /containers/<id>              Change a container's state
PATCH /images/<id>                  Change a specific image's attributes

DELETE /containers/<id>             Delete a specific container
DELETE /containers                  Delete all containers (including running)
DELETE /images/<id>                 Delete a specific image
DELETE /images                      Delete all images

"""

#List all containers, all or just running
@app.route('/containers', methods=['GET'])
def containers_index():
    """
    List all containers

    curl -s -X GET -H 'Accept: application/json' http://localhost:5000/containers | python -mjson.tool
    curl -s -X GET -H 'Accept: application/json' http://localhost:5000/containers?state=running | python -mjson.tool

    """
    #Check whether request requires just running containers or all
    if request.args.get('state') == 'running':
        output = docker('ps')
        resp = json.dumps(docker_ps_to_array(output))

    else:
        output = docker('ps', '-a')
        resp = json.dumps(docker_ps_to_array(output))

    return Response(response=resp, mimetype="application/json")

#Display all images
@app.route('/images', methods=['GET'])
def images_index():
    """
    List all images

    Complete the code below generating a valid response.

    curl -s -X GET -H 'Accept: application/json' http://localhost:5000/images | python -mjson.tool
    """

    output = docker('images')
    resp = json.dumps(docker_images_to_array(output))

    return Response(response=resp, mimetype="application/json")

#Inspect a container
@app.route('/containers/<id>', methods=['GET'])
def containers_show(id):
    """
    Inspect specific container

    curl -s -X GET -H 'Accept: application/json' http://localhost:5000/containers/<id> | python -mjson.tool
    """

    output = docker('inspect', id)

    resp = json.dumps(docker_logs_to_object(id, output))

    return Response(response=resp, mimetype="application/json")


#View logs of a specific container
@app.route('/containers/<id>/logs', methods=['GET'])
def containers_log(id):
    """
    Dump specific container logs

    curl -s -X GET -H 'Accept: application/json' http://localhost:5000/containers/<id>/logs | python -mjson.tool
    """

    output = docker('logs', id)

    resp = json.dumps(docker_logs_to_object(id,output))
    return Response(response=resp, mimetype="application/json")

#Remove an image
@app.route('/images/<id>', methods=['DELETE'])
def images_remove(id):
    """
    Delete a specific image

    curl -s -X DELETE http://localhost:5000/images/<id>
    """

    output = docker ('rmi', id)
    resp = '{"id": "%s",' % id
    output = output.strip('\n')
    resp = resp + '"output": :%s"}' % output
    return Response(response=resp)

#Remove a container
@app.route('/containers/<id>', methods=['DELETE'])
def containers_remove(id):
    """
    Delete a specific container - must be already stopped/killed

    curl -s -X DELETE http://localhost:5000/containers/<id>
    """

    output = docker ('rm', id)
    resp = '{"id": "%s",\n' % id
    output = output.strip('\n')
    resp = resp + '"output ":" %s"}' % output
    return Response(response=resp)

#Remove all containers
@app.route('/containers', methods=['DELETE'])
def containers_remove_all():
    """
    Force remove all containers - dangerous!

    curl -s -X DELETE -H 'Accept: application/json' http://localhost:5000/containers | python -mjson.tool
    """

    #get all container ids
    output = docker('ps','-a')

    #format as array
    containers = docker_ps_to_array(output)

    resp = []

    #loop through array, remove each container with force, append the output to response
    for c in containers:
	single = {}
	single['id'] = c['id']
    	output = docker('rm','-f',c['id'])
	output = output.strip('\n')
	resp.append(single['id'] + ': ' + output)

    resp = json.dumps(resp)
    return Response(response=resp, mimetype="application/json")

#Remove all images
@app.route('/images', methods=['DELETE'])
def images_remove_all():
    """
    Force remove all images - dangrous!

    curl -s -X DELETE -H 'Accept: application/json' http://localhost:5000/images | python -mjson.tool
    """
    #get all images
    output = docker('images')

    #format as array
    images = docker_images_to_array(output)

    resp = []

    #loop through array, remove each image with force and append the output to response
    for i in images:
	single = {}
	single['id'] = i['id']
	output = docker('rmi','-f',i['id'])
	output = output.strip('\n')
	resp.append(single['id']+': '+output)

    resp = json.dumps(resp)
    return Response(response=resp, mimetype="application/json")


@app.route('/containers', methods=['POST'])
def containers_create():
    """
    Create container (from existing image using id or name)

    curl -X POST -H 'Content-Type: application/json' http://localhost:5000/containers -d '{"image": "<name>"}'
    curl -X POST -H 'Content-Type: application/json' http://localhost:5000/containers -d '{"image": "<id>"}'
    curl -X POST -H 'Content-Type: application/json' http://localhost:5000/containers -d '{"image": "<name/id>","publish":"<port>"}'

    """

    #get image name
    body = request.get_json(force=True)
    image = body['image']

    #check if publish exists in the json, init args appropriately
    if 'publish' not in body:
        args = ('run', '-d', image)
    else:
        port = body['publish']
        args = ('run', '-d','-p', port, image)

    #run command with args, receive response limited to 12 characters, the id.
    output = docker(*(args))
    id = output[0:12]
    resp = '{"id": "%s",' % id
    output = output.strip('\n')
    resp = resp + '"output": "%s"}' % output

    return Response(response=resp)


@app.route('/images', methods=['POST'])
def images_create():
    """
    Create image (from uploaded Dockerfile)

    curl -H 'Accept: application/json' -F file=@Dockerfile http://localhost:8080/images

    """

    #get file
    dockerfile = request.files['file']

    #get folder
    folder = 'dockerfiles'
    file = dockerfile.filename

    #create folder if it doesn't exist already
    if(not os.path.exists(folder)):
	os.makedirs(folder)

    #join the folder and file to get a path
    path = os.path.join(folder,file)

    #save uploaded file to this path
    dockerfile.save(path)

    #split on . so we can get the name without the extension
    noext = file.split('.')

    #build using the new file
    output = docker('build', '-f', path, '-t',noext[0], '.')

    #get id of newly created image
    output = docker('images', noext[0], '-aq')
    id = output[0:12]
    resp = '{"id": "%s",' % id
    output = output.strip('\n')
    resp = resp + '"output": "%s"}' % output
    return Response(response=resp, mimetype="application/json")



#Stop or start a specific container
@app.route('/containers/<id>', methods=['PATCH'])
def containers_update(id):
    """
    Update container attributes (support: state=running|stopped)

    curl -X PATCH -H 'Content-Type: application/json' http://localhost:5000/containers/<id> -d '{"state": "running"}'
    curl -X PATCH -H 'Content-Type: application/json' http://localhost:5000/containers/<id> -d '{"state": "stopped"}'

    """

    #check which instruction is received, run appropriate docker command
    body = request.get_json(force=True)
    try:
        state = body['state']
        if state == 'running':
            output = docker('restart', id)
	if state =='stopped':
	    output = docker('stop', id)
    except:
        pass

    resp = '{"id": "%s",' % id
    output = output.strip('\n')
    resp = resp + '"output": "%s"}' % output
    return Response(response=resp, mimetype="application/json")

#update the tag of an image
@app.route('/images/<id>', methods=['PATCH'])
def images_update(id):
    """
    Update image attributes (support: name[:tag])  tag name should be lowercase only

    curl -s -X PATCH -H 'Content-Type: application/json' http://localhost:8080/images/<id> -d '{"tag": "test:1.0"}'
    """
    #get the new tag
    data = request.get_json(force=True)
    tag = data['tag']

    #tag the image
    output = docker('tag',id,tag)

    resp = '{"id": "%s",' % id
    output = output.strip('\n')
    resp = resp + '"output": "%s"}' % output
    return Response(response=resp, mimetype="application/json")


def docker(*args):
    cmd = ['docker']
    for sub in args:
        cmd.append(sub)
    process = Popen(cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    if stderr.startswith('Error'):
        print 'Error: {0} -> {1}'.format(' '.join(cmd), stderr)
    return stderr + stdout

# 
# Docker output parsing helpers
#

#
# Parses the output of a Docker PS command to a python List
# 
def docker_ps_to_array(output):
    all = []
    for c in [line.split() for line in output.splitlines()[1:]]:
        each = {}
        each['id'] = c[0]
        each['image'] = c[1]
        each['name'] = c[-1]
        each['ports'] = c[-2]
        all.append(each)
    return all

#
# Parses the output of a Docker logs command to a python Dictionary
# (Key Value Pair object)
def docker_logs_to_object(id, output):
    logs = {}
    logs['id'] = id
    all = []
    for line in output.splitlines():
        all.append(line)
    logs['logs'] = all
    return logs

#
# Parses the output of a Docker image command to a python List
# 
def docker_images_to_array(output):
    all = []
    for c in [line.split() for line in output.splitlines()[1:]]:
        each = {}
        each['id'] = c[2]
        each['tag'] = c[1]
        each['name'] = c[0]
        all.append(each)
    return all

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=5000, debug=True)
