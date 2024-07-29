
# Process to run Nodes of NIG network

Process to intall and run locally 3 Nodes of the NIG network
Technical details can be found here https://docs.google.com/document/d/e/2PACX-1vTO0nKIogxFLGWkN0QpaMsGsg9Cp-Aqfv31sc6p_HQnb7tShmqymOM05o3_7YCFkBY7GIipWSNO756d/pub

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

All the technical documentation can be found in the docs folder. You will find the document for the 3 main modules:
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
