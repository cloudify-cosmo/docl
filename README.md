# docl

## Prerequisites
* Docker should be installed and running.
* Current user should be added to the `docker` group (`sudo` is not used in `docl` when running  `docker`)

## Installation
`docl` can be installed by running 

```
pip install docl
```

Note that `cloudify` CLI is a dependency of `docl`.

## Initial Configuration

Run `docl init` and supply the different configuration options based on your setup.
* `--simple-manager-blueprint-path` is mandatory and will be used when running `docl bootstrap`
* `--ssh-key-path` should point to a private key that will have access to created containers.
* `--docker-host` should point to the docker endpoint. By default it will use `fd://` which means it will use a local socket. To use the
  `dockercompute` plugin later to install docker based agents, you should consider starting docker with a tcp based host.
* `--source-root` should point to the root directory in which all cloudify related projects are cloned. This is used for mounting code
  from the host machine to the relevant manager directories.

## Usage

After the initial configuration, most commands don't require any additional configuration to work with.

### `docl bootstrap`
To bootstrap a manager a manager using the simple manager blueprint suppplied during initial configuration, simply run


```
docl bootstrap
```

### `docl prepare`
If you want to bootstrap on your own, create an empty container (CentOS 7 with systemd and ssh enabled suitable for bootstrap), by 
running

```
docl prepare
```

This will start a container and generate an inputs file `inputs.yaml` that can be used to manually bootstrap the manager using the simple manager blueprint.

### `docl save-image`

After running `docl bootstrap`, run

```
docl save-image
```

To create an manager image from the currently installed manager. This step is required for mounting user code on manager containers.

You can pass the optional `--prepare-agent` flag to the `save-image` command if you intend to make changes that apply to agent packages as well. This will prepare the manager image so that other commands can later easily build agent packages based on recent code.

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
