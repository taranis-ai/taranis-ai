# Installation

This repository provides an automated way of installing Taranis NG.

## 1 Introduction

Taranis NG is internally comprised of several components:

- **API** - a RESTful API server, providing the core functionality of Taranis NG
- **GUI** - a web page that provides the user interface
- **Collectors, Presenters, Publishers** - separate apps, that facilitate communication of Taranis NG with outside world
- **Bots** - external tools, that improve on the features of Taranis NG by using the same API calls the GUI is using. Bots are optional.

Also, there is one more component that is external to Taranis NG software, but is used to authenticate users. It's not strictly needed for just evaluating Taranis NG - you can use a simple built-in internal authenticator for that.

- **External Authentication and Authorization** - an external application that Taranis NG trusts to provide user identities and validate their credentials. We recommend an open-source software [Keycloak](https://www.keycloak.org/). And yes, you can also log into Taranis NG using Google, Facebook or Microsoft login, and more.

All of these components may be installed on separate hosts, or together on one host.


## 2 Brave, impatient, localhost TL;DR installation

Installation instructions for the impatient. Use at your own risk. Skip to the next section for a more detailed manual, and a proper way of doing things.

```
git clone https://gitlab.com/sk-cert/taranis-ng-utils.git
cd taranis-ng-utils
ansible-playbook \
   -i inventory/localhost.yml \
   playbooks/install-localhost.yml
```

Done, now visit [http://www.taranisng.local](http://www.taranisng.local), login with one of

- admin/admin
- user/user
- customer/customer

## 3 How to install

### 3.1 Install Ansible and GIT (skip if you already have it)

Install the latest version of Ansible. [Ansible installation instructions](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html) are different from system to system, but generally it's something along the `apt install ansible`, `brew install ansible`, `yum install ansible`, `pkg install ansible` lines.

Install the command line tool `git`.

### 3.2 Prepare your target hosts

Make your physical servers, or VMs ready. 

- use **Ubuntu 18.04** and **Ubuntu 20.04**, which are currently supported.
- enable ssh service
- create an account for installation
- install public ssh key to that account
- make sure the account can sudo to root

You can install Taranis NG components (API, GUI, collectors, presenters, publishers, and other) on separate hosts, or install everything on a single host. As a special case, you can of course install on the node where you run the installation playbook.

### 3.3 Setup DNS entries

Don't forget to setup the DNS entries, or add the IP addresses into `/etc/hosts`.

You will typically need at least two domain names: www.* and api.*, pointing to the right IP addresses.

### 3.4 Clone this repository

Clone and change the working directory to the recently cloned repository.

```
git clone https://gitlab.com/sk-cert/taranis-ng-utils.git
cd taranis-ng-utils
```

### 3.5 Edit the inventory file to point to your host(s)

Edit one of the files

  - [inventory/localhost.yml](inventory/localhost.yml) for local installation
  - [inventory/simple.yml](inventory/simple.yml) to install everything in one host, or
  - [inventory/distributed.yml](inventory/distributed.yml) for installation split to various hosts.
 
Here are some sample entries:

```
all:
  hosts:
    www.taranisng.example:
      ansible_user: pikula
      ansible_python_interpreter: python3

    api.taranisng.example:
      ansible_host: 192.168.10.1
      ansible_user: taranisng
```

- `ansible_python_interpreter` - python3 is needed on target hosts anyway, and installation using python3 is easier. If your target defaults to python3, you can safely omit this line.
- `ansible_host` - use if the hosts are not reachable via DNS or entry in /etc/hosts. DNS or entry in /etc/hosts will most likely be needed in order to actually use the product anyway.

For other questions, please refer to [Ansible documentation](https://docs.ansible.com/).

### 3.6 Set configurables

Edit the variables in [ansible-sample-installation-playbook.yml](ansible-sample-installation-playbook.yml). Take care to change the hostname for API and GUI according to your environment, and also generate strong passwords for database and JWT tokens.

If proxy is required, add a block like this:

```
  environment:
    http_proxy: "http://proxy.int.sk-cert.sk:3128/"
    https_proxy: "http://proxy.int.sk-cert.sk:3128/"
    ftp_proxy: "http://proxy.int.sk-cert.sk:3128/"
    HTTP_PROXY: "http://proxy.int.sk-cert.sk:3128/"
    HTTPS_PROXY: "http://proxy.int.sk-cert.sk:3128/"
    FTP_PROXY: "http://proxy.int.sk-cert.sk:3128/"
```

Comment or uncomment the "sample data" role.

### 3.7 Install!

Depending on a chosen inventory and installation type, run one of the following:

To install on localhost:

```
ansible-playbook \
   -i inventory/localhost.yml \
   playbooks/install-localhost.yml
```

To install everything on a single machine:

```
ansible-playbook \
   -i inventory/simple.yml \
   playbooks/install-simple.yml
```

To install each component separately on its own host:

```
ansible-playbook \
   -i inventory/distributed.yml \
   playbooks/install-distributed.yml
```

#### Known bugs and caveats

- one of the latest installation steps, sample data, currently fails. Quick fix is provided during the installation.
- reboot is required after installation.
- sample data installs corrupted collector configuration; go to collector nodes and re-save to fix it.
- beware: if you enable keycloak, some manual configuration is needed.

# 4 Extras and future work

## 4.1 Docker

You can install Taranis NG inside the docker containers, then create images from these containers. While the `Dockerfile` is not provided, the Ansible playbooks can be used to install the software inside of the containers. The process has three steps:

- create the necessary containers, using ubuntu-based python images
- install the software inside the containers using Ansible
- run `docker commit container_id image_name:version3`

See the sample [inventory/distributed-docker.yml](inventory/distributed-docker.yml) for hints.

## 4.2 How to contribute

We welcome any kind of contribution, but feel much can be done in these areas:

- testing and writing detailed bug reports
- developing a proper Dockerfile
- translating Taranis NG to other languages
- generalizing the Ansible installation roles to install Taranis NG on more distributions, and even operating systems