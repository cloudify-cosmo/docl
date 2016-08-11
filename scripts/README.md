# dockerify.py

In order to quickly test changes to manager components, you can use the `dockerify.py` script to spin up a manager as a docker container.


## Prerequisites:
- [docker](https://www.docker.com/)
    - (your user must be authorized to use docker: `adduser $USER docker`)
- `cfy` in your `$PATH`
    - (running the `install_packages.py` script will sort that out for you, but you may also wish to refer to the [dev environment setup guide](guides/dev-environment))
- pyyaml
    - `pip install pyyaml`
- a local copy of a manager blueprint
    - `git clone https://github.com/cloudify-cosmo/cloudify-manager-blueprints`
- an SSH key
    - if you don't have this already, run `ssh-keygen`


## Usage:
```bash
$ python dockerify.py cloudify-manager-blueprints/simple-manager-blueprint.yaml

# For help on additional options:
$ python dockerify.py --help
```

The script will open ports `80`, `443`, and `5671` and forward those ports from your host to the container ("publish" them, in docker's terms).
It will also open port `22` but only locally, so you will need to use the docker local IP address to SSH in to the container
(this is printed just before the script finishes, or it can be found by running `docker inspect ${container_name} | grep IPAddress`).

Your `id_rsa` key (or another key that you provided, see `python dockerify.py --help`) will allow you to SSH in to the `root` account in the container, or you can use any docker commands you are comfortable with.


## Cleaning up
This script will not automatically clean up a manager container if you run it again. Use the regular docker commands to do so:
```bash
$ docker ps
#Example output:
#CONTAINER ID        IMAGE                       COMMAND             CREATED             STATUS              PORTS                                                                      NAMES
#aaa43b668548        cloudify/centos-manager:7   "/sbin/init"        30 hours ago        Up 30 hours         0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp, 22/tcp, 0.0.0.0:5671->5671/tcp   distracted_swirles
$ docker rm -f distracted_swirles # insert the name or ID of your container here
# or use docker stop followed by docker rm
```
