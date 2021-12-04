# HeadHunter-API


**Code collects salary figures for vacancies from two sources:** [HeadHunter](https://hh.ru), [SuperJob](https://www.superjob.ru).


This script is written as part of the task of the courses [Devman](https://dvmn.org).


## Getting Started

These instructions will get you a copy of the project up and running on your local machine.

### Python Version

Python 3.6 and later.

### Installing

To install the software, you need to install the dependency packages from the file: **requirements.txt**.

Perform the command:

```

pip3 install -r requirements.txt

```


## Getting API key

**API key SuperJob**

- To get the API key. You need to log in to the API service SuperJob link: [`SuperJob`](https://api.superjob.ru/info/).
- On the API page , fill out the form and get API key.


### Connecting the API key

You need to create a `.env` file and write all sensitive data into it, like this:

```python
API_KEY_SUPERJOB="v3.h.4249508.8bb4144bfc13d74a77c9b169a4a4a852f7f17007
```

## Launch code

```python
$ python api_head_hunter.py

```

#### Arguments
- Set the vacancies use arguments: **-v** or **--vacancy**
- - Set the period use arguments: **-p** or **--period**
- To call help, use the required arguments **-h** or **--help**


**Examples of commands:**

```python
$ python api_head_hunter.py -v javascript

```
**Multiple set:**

```python
$ python api_head_hunter.py -v javascript c++ python

```

```python
$ python api_head_hunter.py -v javascript c++ python -p 7

```

Running code without arguments the default period is 30 days.

By default, a set of vacancies by keywords is set:

"python", "javascript", "golang", "java", "c++", "typescript", "c#"

```python
$ python api_head_hunter.py

```


## Authors

**vlaskinmac**  - [GitHub-vlaskinmac](https://github.com/vlaskinmac/)


