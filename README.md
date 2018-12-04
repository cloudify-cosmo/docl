# docl

## Prerequisites
* Docker should be installed and running. It should be started with root privileges because containers are started with the `--privileged` flag.

### TCP socket configuration
Docker should be also accessible on tcp along with the default unix socket, to achieve this:
* Create the file `/etc/systemd/system/docker.service.d/startup_options.conf` (if required create the parent directory)
* Input the below contents:
```
# /etc/systemd/system/docker.service.d/override.conf
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd -H unix:// -H tcp://0.0.0.0:2375
```
* Run:
```
sudo systemctl daemon-reload
sudo systemctl restart docker.service
```
* Validate docker listens on the unix socket and the tcp socket (both commands should print the installed docker version):
```
docker -H tcp://127.0.0.1:2375 version
sudo docker version
```  

## Installation
`docl` can be installed by running 

```
pip install docl
```

Note that `cloudify` CLI is a dependency of `docl`.

## Initial Configuration

Run `docl init` and supply the different configuration options based on your setup.
* `--ssh-key-path` should point to a private key that will have access to created containers.
* `--docker-host` should point to the docker endpoint.
* `--source-root` should point to the root directory in which all cloudify related projects are cloned. This is used for mounting code
  from the host machine to the relevant manager directories.
* (Optional) `[-m]|[--manager-image-docker-tag]` Default Docker image tag to use (for example `docl run` with no parameters will use this value to run a local image with this tag).
* (Optional) `[-u]|[--manager-image-url]` URL to the docker manager image. This must be set when using a dev feature. This will download the specified image when running `docl pull-image`.
* (Optional, for a development branch) `[-a]|[--manager-image-commit-sha-url]` URL to the `sha1` checksum. This can save time if specified image already downloaded when 
the `--manager-image-url` is set. 

## Usage

After the initial configuration, most commands don't require any additional configuration to work with.

### `docl bootstrap`
To bootstrap a manager a manager using an install RPM available in `cloudify-premium`, simply run


```
docl bootstrap
```

`bootstrap` accepts a `--serve-install-rpm` flag that will download the install RPM locally and will act as a local file server during the bootstrap process. The install RPM will not be re-downloaded if it already exists unless the invalidate cache flag (`--serve-install-rpm-invalidate-cache`) is supplied as well.

### `docl prepare`
If you want to bootstrap on your own, create an empty container (CentOS 7 with systemd and ssh enabled suitable for bootstrap), by 
running

```
docl prepare
```

This will start a container and generate a config file `config.yaml` that can be used to manually install a manager using an install RPM (copying the file to the container).

### `docl save-image`

After running `docl bootstrap`, run

```
docl save-image
```

To create an manager image from the currently installed manager. This step is required for mounting user code on manager containers.

If you started a container by running `docl run` and made some changes to it that you'd like to perserve, you can run `docl save-image` as well.


### `docl pull-image`

To pull the latest built image from S3 (instead of running `bootstrap` and then `save-image` to create your own image), run

```
docl pull-image
```

Using a dev branch:
1. You must run `docl init ... [-u]|[--manager-image-url] <URL_OF_DOCL_IMAGE> [[-a]|[--manager-image-commit-sha-url] <CHECKSUM_URL_OF_DOCL_IMAGE>]`
2. Run `docl pull-image`

_Note: if `--manager-image-url` has been set at `docl init` then `docl` will download the image located at the `manager-image-url` URL provided._

### `docl run`

To start a new manager container based on the last image created using `save-image` run

```
docl run
```

If you want the container to start with directories mounted based on code residing on the host machine, supply the optional `--mount`
flag.

### `docl install-docker`

To install docker within a running container (used by the integration tests), run

```
docl install-docker
```

You may pass the optional `--version` flag to install a specific version, otherwise, the version installed on the host machine
will be installed on the container.

### `docl clean`

To remove all containers started by `docl`, run

```
docl clean
```

Note that the image saved by running `docl save-image` will still be available to you.

### `docl restart-services`
If a manager was started using `docl run --mount` you may need to restart certain services after making code changes. One option to do so is to run

```
docl restart-services
```

### `docl ssh`
To `ssh` into a container created by `docl`, run 

```
docl ssh
```

### `docl build-agent`
If you want to create a new `centos` based agent package on a manager container that was started using `docl run --mount`, run

```
docl build-agent
```

### `docl watch`
This command is blocking and will monitor changes made to any package that is mounted on the manager container. On changes, it will
restart relevant services for you so you don't have to run `docl restart-services` every time.

If you want the centos agent package to be built as well on changes to relevant packages that affect the agent package, supply the 
optional `--rebuild-agent` flag to the `watch` command.

### `docl exec`
To execute a command on a container, run

```
docl exec <COMMAND>
```

### `docl cp`
To copy a file from or to a container, run 

```
docl cp SOURCE_PATH TARGE_PATH
```
If you wish to copy from the container, prefix the `SOURCE_PATH` with `:`, If you wish to copy to the container, prefix the `TARGET_PATH` with `:`.

For example, to copy `/tmp/some_file` from the host machine to a container on `/root/configuration.txt`, run

```
docl cp /tmp/some_file :/root/configuration.txt
```
