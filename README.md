

# What is NIG ?
The NIG project aims to remunerate the money lying dormant in current bank accounts through the regular use of a cryptocurrency. Discover how in this [document ](https://docs.google.com/document/u/1/d/e/2PACX-1vQxiyzQCp9qEkBbHT5wjt_YTXvRXycus77Z4M8pxd5Lp6JpI3ZjSq5bJMlRCUAx-3pRjr6kkByBG4HN/pub?urp=gmail_link) (in French).


## Process to run Nodes of NIG network

Process to install and run locally 3 Nodes of the NIG network

## Authors

- [@Crypto_NIG](https://github.com/nigcrypto)


## Run Locally

Install [Python 3.11.4](https://www.python.org/downloads/release/python-3114/)

Clone the project

```bash
  git clone https://github.com/project-nig/beta_node.git
```

Rename the folder beta_node to nodeX where X corresponds to the number of the node (ex: 1 then 2 and finally 3)

```bash
  MOVE beta_node nodeX
```

Go to the project directory nodeX with administrator privilige (right click on Command Prompt in windows)

```bash
  cd nodeX
```

Create a Virtual Environment and activate it

```bash
  python -m venv env
  env\scripts\activate
```

Install dependencies

```bash
  pip install --upgrade pip
  pip install -r requirements.txt
```
Change the parameter in the file nodeX\src\common\values.py

```bash
  change the below parameter where X corresponds to the number of the node (ex:1)

  MY_NODE="local_nodeX"
  MY_HOSTNAME = '127.0.0.X:5000'
  NODE_FILES_ROOT = r'C: path to \nig\nodeX'

  save the file
```
Start the node

```bash
  env\scripts\activate
  set FLASK_APP=src/node/main.py
  flask run --host=127.0.0.X 
  where X corresponds to the number of the node (ex:1)
```
The default blockchain is available on http://127.0.0.X:8000/block

Create 2 others Node in the **same folder !** than the first node. Your root directory should be like that:
```bash
  \node1\
  \node2\
  \node3\
```
Launch 2 others Node in their respective folder.
```bash
  Start all the tasks from cloning the projet until the start of the node
  Replace X all the times with 2 for 2nd Node and then 3 for the third node
```

## Documentation
### Overview
An overview of the [technical details](https://docs.google.com/document/d/e/2PACX-1vTO0nKIogxFLGWkN0QpaMsGsg9Cp-Aqfv31sc6p_HQnb7tShmqymOM05o3_7YCFkBY7GIipWSNO756d/pub) is available (in French).

### Visual Diagrams
Several diagrams are available to better understand the interactions between the Class, Object, Method, etc
>How the [NIG Network](https://viewer.diagrams.net/?tags=%7B%7D&lightbox=1&highlight=0000ff&edit=_blank&layers=1&nav=1&title=10_Network#Uhttps%3A%2F%2Fdrive.google.com%2Fuc%3Fid%3D1YCxaD_aJYUuVm_GbWdbpG3JfiKawxqzH%26export%3Ddownload) is initialized.

>How a [transaction](https://viewer.diagrams.net/?tags=%7B%7D&lightbox=1&highlight=0000ff&edit=_blank&layers=1&nav=1&title=20_Transaction#Uhttps%3A%2F%2Fdrive.google.com%2Fuc%3Fid%3D10RUXVQOz87zV22Xx90fcjsxpcc8i8BDU%26export%3Ddownload) is made on the NIG network.

>How a [SmartContrat](https://viewer.diagrams.net/?tags=%7B%7D&lightbox=1&highlight=0000ff&edit=_blank&layers=1&nav=1&title=30_SmartContract#Uhttps%3A%2F%2Fdrive.google.com%2Fuc%3Fid%3D1YR6M7MIu7n4pt269-hX9uLMw77VWmCm8%26export%3Ddownload) works.

>How a [block](https://viewer.diagrams.net/?tags=%7B%7D&lightbox=1&highlight=0000ff&edit=_blank&layers=1&nav=1&title=40_Consensus#Uhttps%3A%2F%2Fdrive.google.com%2Fuc%3Fid%3D1PAuhT8yiuq6xpoJQFgIaSYyvfa_OMV_1%26export%3Ddownload) is created.

>How the [consensus](https://viewer.diagrams.net/?tags=%7B%7D&lightbox=1&highlight=0000ff&edit=_blank&layers=1&nav=1&title=50_Consensus#Uhttps%3A%2F%2Fdrive.google.com%2Fuc%3Fid%3D1uwMwq3o3VKVH7_VKYrz4V1l2TDzQvPfs%26export%3Ddownload) is made between the nodes.

>How the [reputation](https://viewer.diagrams.net/?tags=%7B%7D&lightbox=1&highlight=0000ff&edit=_blank&layers=1&nav=1&title=60_reputation#Uhttps%3A%2F%2Fdrive.google.com%2Fuc%3Fid%3D1KvKRZDreXp_firoid9yPMhXi8v00C7ai%26export%3Ddownload) is managed (in French).

All the technical documentation can be found in the docs folder. Once you have cloned locally the files, clicking on each file will open a web interface to navigate through the code. You will find the document for the 3 main modules :
```bash
	common in common.html
	node in node.html
	wallet in wallet.html
```

## Hello world example

A very basic Hello world example to explain how to generate a purchase request on the Marketplace can be found [here](HELLOWORLD.md).

## Contribute to the Development

New contributors are very welcome and needed. Check out the [good first issue](https://github.com/project-nig/beta_node/issues?q=is%3Aopen+is%3Aissue+label%3A%22good+first+issue%22) to easily see how you can [contribute](CONTRIBUTING.md).


## Running Integration tests

Install Pytest => https://docs.pytest.org/

Launch your network by running 3 nodes locally (cf. previous Process to run Nodes of NIG network).

Open a new command prompt an go to the folder of the 3rd Node.
```bash
  \node3>
```
Launch the virtual environment.
```bash
  env\scripts\activate
```
Launch the integration test scripts.
```bash
  tox -e integration
```
If everything goes well, you should have a report validating your development. If not, the errors will be explained.

## Documentation

Project NIG is using [pdoc](https://pdoc.dev/docs/pdoc.html) for generating the documentation. Here the process:
```bash
  start your node at least once
  run pdoc ./src/common/ -o ./docs for the documentation in common folder
  run pdoc ./src/node/ -o ./docs for the documentation in node folder
  delete the file index.html in folders \docs
```
## Scripts for testing

Some scripts are available in the folder [testing_scripts](/testing_scripts) to ease the reset of your testing environment. 

### Setup to do once
Move all the content of the folder *testing_scripts* in to the root directory where the code of your 3 nodes is stored. Your root directory should be now like this:
```bash
  \node1\
  \node2\
  \node3\
  \values_temp\
  \back-up_values.bat
  \copy_env.bat
  \copy_env_WO_values.bat
```
Open each script file (.bat) and replace *"....path to source folder..."* by the real **path to the root folder** where all the code of the 3 node is stored.

If you have already successfully started the 3 nodes, launch this script:
```bash
  back-up_values.bat
```
This will back_up the *values.py* file of *node1* and *node2* into the folder *values_temp* which will be used each time that you reset your testing environment.
### Process to follow each time you want to reset the testing environment
click on this script:
```bash
  copy_env.bat
```
This will copy all the code from the *node3* into *node1* and *node2* and the *values.py* file from their respective directory *nodeX* in the *values_temp* folder in their *nodeX* folder at the root. Please be aware that your **working environment is always node3 !**. Never update the code in node1 and node2 as it will be overwritten with the scripts.

Then you need to restart your 3 nodes by using the below python script where X corresponds to the number of the node (ex:1 then 2 and finally 3)
```bash
\nodeX\flask run --host=127.0.0.X
```

Each time that you're changing a parameter in the *values.py* of node3, you have 2 options:

 - Option 1: make the same change in the *values.py* of node1 and node2. Launch this script:

```bash
  back-up_values.bat
```
 - Option 2: launch the below script:

```bash
  copy_env_WO_values.bat
```
follow the procedure called "*Change the parameter in the file nodeX\src\common\values.py*" described in [run-locally](/beta_node?tab=readme-ov-file#run-locally) in order to configure properly all the *values.py* file of each node.

## Feedback

If you have any feedback, please reach out to us at cryptomonnaie.nig@gmail.com
