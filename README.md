# What is NIG ?
The NIG project aims to remunerate the money lying dormant in current accounts through the regular use of a cryptocurrency discover how in this [document ](https://docs.google.com/document/u/1/d/e/2PACX-1vQxiyzQCp9qEkBbHT5wjt_YTXvRXycus77Z4M8pxd5Lp6JpI3ZjSq5bJMlRCUAx-3pRjr6kkByBG4HN/pub?urp=gmail_link) (in French).


## Process to run Nodes of NIG network

Process to intall and run locally 3 Nodes of the NIG network

## Authors

- [@Crypto_NIG](https://github.com/nigcrypto)


## Run Locally

Install Python 3.11.4 => https://www.python.org/downloads/release/python-3114/

Clone the project

```bash
  git clone https://github.com/project-nig/beta_node.git
```

Rename the folder beta_node to nodeX where X corresponds to the number of the node (ex:1n then 2 and finally 3)

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

Launch 2 others Node
```bash
  Start all the tasks from cloning the projet until the start of the node
  Replace X all the times with 2 for 2nd Node and then 3 for the third node
```

## Documentation
### Overview
An overiew of the [technical details](https://docs.google.com/document/d/e/2PACX-1vTO0nKIogxFLGWkN0QpaMsGsg9Cp-Aqfv31sc6p_HQnb7tShmqymOM05o3_7YCFkBY7GIipWSNO756d/pub) is available (in French).

### Visual Diagrams
Several viusal diagrams are available to better understand the interactions between the Class, Object, Method, etc
>How the [NIG Network](https://viewer.diagrams.net/?tags=%7B%7D&lightbox=1&highlight=0000ff&edit=_blank&layers=1&nav=1&title=10_Network#Uhttps%3A%2F%2Fdrive.google.com%2Fuc%3Fid%3D1YCxaD_aJYUuVm_GbWdbpG3JfiKawxqzH%26export%3Ddownload) is initialized

>How a [transaction](https://viewer.diagrams.net/?tags=%7B%7D&lightbox=1&highlight=0000ff&edit=_blank&layers=1&nav=1&title=20_Transaction#Uhttps%3A%2F%2Fdrive.google.com%2Fuc%3Fid%3D10RUXVQOz87zV22Xx90fcjsxpcc8i8BDU%26export%3Ddownload) is made on the NIG network.

>How a [SmartContrat](https://viewer.diagrams.net/?tags=%7B%7D&lightbox=1&highlight=0000ff&edit=_blank&layers=1&nav=1&title=30_SmartContract#Uhttps%3A%2F%2Fdrive.google.com%2Fuc%3Fid%3D1YR6M7MIu7n4pt269-hX9uLMw77VWmCm8%26export%3Ddownload) works.

>How a [block](https://viewer.diagrams.net/?tags=%7B%7D&lightbox=1&highlight=0000ff&edit=_blank&layers=1&nav=1&title=40_Consensus#Uhttps%3A%2F%2Fdrive.google.com%2Fuc%3Fid%3D1PAuhT8yiuq6xpoJQFgIaSYyvfa_OMV_1%26export%3Ddownload) is created.

>How the [consensus](https://viewer.diagrams.net/?tags=%7B%7D&lightbox=1&highlight=0000ff&edit=_blank&layers=1&nav=1&title=50_Consensus#Uhttps%3A%2F%2Fdrive.google.com%2Fuc%3Fid%3D1uwMwq3o3VKVH7_VKYrz4V1l2TDzQvPfs%26export%3Ddownload) is made between the nodes

>How the [reputation](https://viewer.diagrams.net/?tags=%7B%7D&lightbox=1&highlight=0000ff&edit=_blank&layers=1&nav=1&title=60_reputation#Uhttps%3A%2F%2Fdrive.google.com%2Fuc%3Fid%3D1KvKRZDreXp_firoid9yPMhXi8v00C7ai%26export%3Ddownload) is managed (in French).

All the technical documentation can be found in the docs folder. Once you have cloned locally the files, clicking on each file will open a web interface to navigate through the code. You will find the document for the 3 main modules :
```bash
	common in common.html
	node in node.html
	wallet in wallet.html
```

## Performing Development

Clone the master Branch.

Perform your development locally and commit your change on the master branch which will be published once approved.


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

## Feedback

If you have any feedback, please reach out to us at cryptomonnaie.nig@gmail.com
