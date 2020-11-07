Ben Ryan - C15507277
IP:Port: 
Github: https://github.com/benr96/CloudComputingAssignment2
Video: https://youtu.be/byXBfS57IKk

Part 1:
	1. On manager run: 'docker swarm init'
	   On the workers run: 'docker swarm join --token' followed by the token supplied by the manager
	
	2. DockerCMS file is in the github, when running it can be tested using cmsTester.
	
Part 2:
	1. On the manager run: 'docker service create --replicas 5 -p 80:80 --name web nginx'
	   Status can be viewed on the visualizer.
	  
	2. The bash file for testing the CMS is in the github. The command runs in order of the index page.
	   It will ask for input of IDs or states to change, the ids can be taken from the previous commands output.
	   test.Dockerfile can be used to upload and use for creating the image.
	   
I have not completed the extra question, part 3.
	   
