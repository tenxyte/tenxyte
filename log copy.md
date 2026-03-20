Read the Docs build information
Build id: 31894029
Project: tenxyte
Version: latest
Commit: 916401ac026cb500333a55dec18aab529567abcc
Date: 2026-03-20T10:07:48.917201Z
State: finished
Success: False


[rtd-command-info] start-time: 2026-03-20T10:07:49.401151Z, end-time: 2026-03-20T10:07:49.925083Z, duration: 0, exit-code: 0
git clone --depth 1 https://github.com/tenxyte/tenxyte.git .
Cloning into '.'...

[rtd-command-info] start-time: 2026-03-20T10:07:49.962150Z, end-time: 2026-03-20T10:07:50.848447Z, duration: 0, exit-code: 0
git fetch origin --force --prune --prune-tags --depth 50 refs/heads/main:refs/remotes/origin/main
From https://github.com/tenxyte/tenxyte
 * [new tag]         v0.0.0-test   -> v0.0.0-test
 * [new tag]         v0.9.2        -> v0.9.2
 * [new tag]         v0.9.2.5-core -> v0.9.2.5-core

[rtd-command-info] start-time: 2026-03-20T10:07:50.934754Z, end-time: 2026-03-20T10:07:51.005135Z, duration: 0, exit-code: 0
git checkout --force origin/main
Note: switching to 'origin/main'.

You are in 'detached HEAD' state. You can look around, make experimental
changes and commit them, and you can discard any commits you make in this
state without impacting any branches by switching back to a branch.

If you want to create a new branch to retain commits you create, you may
do so (now or later) by using -c with the switch command. Example:

  git switch -c <new-branch-name>

Or undo this operation with:

  git switch -

Turn off this advice by setting config variable advice.detachedHead to false

HEAD is now at 916401a Merge pull request #85 from tenxyte/feature/framework-agnostic

[rtd-command-info] start-time: 2026-03-20T10:07:51.041928Z, end-time: 2026-03-20T10:07:51.080051Z, duration: 0, exit-code: 0
cat .readthedocs.yaml
# Read the Docs configuration file
# See https://docs.readthedocs.io/en/stable/config-file/v2.html for details

# Required
version: 2

# Set the OS, Python version, and other tools you might need
build:
  os: ubuntu-24.04
  tools:
    python: "3.13"

# Build documentation with MkDocs
mkdocs:
  configuration: mkdocs.yml

# Declare the Python requirements required to build your documentation
python:
   install:
   - requirements: docs/en/requirements.txt

[rtd-command-info] start-time: 2026-03-20T10:07:56.888318Z, end-time: 2026-03-20T10:07:56.946375Z, duration: 0, exit-code: 0
asdf global python 3.13.3


[rtd-command-info] start-time: 2026-03-20T10:07:57.318322Z, end-time: 2026-03-20T10:07:58.037820Z, duration: 0, exit-code: 0
python -mvirtualenv $READTHEDOCS_VIRTUALENV_PATH
created virtual environment CPython3.13.3.final.0-64 in 438ms
  creator CPython3Posix(dest=/home/docs/checkouts/readthedocs.org/user_builds/tenxyte/envs/latest, clear=False, no_vcs_ignore=False, global=False)
  seeder FromAppData(download=False, pip=bundle, setuptools=bundle, wheel=bundle, via=copy, app_data_dir=/home/docs/.local/share/virtualenv)
    added seed packages: pip==23.1, setuptools==67.6.1, wheel==0.40.0
  activators BashActivator,CShellActivator,FishActivator,NushellActivator,PowerShellActivator,PythonActivator

[rtd-command-info] start-time: 2026-03-20T10:07:58.074153Z, end-time: 2026-03-20T10:08:03.111680Z, duration: 5, exit-code: 0
python -m pip install --upgrade --no-cache-dir pip setuptools
Requirement already satisfied: pip in /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/envs/latest/lib/python3.13/site-packages (23.1)
Collecting pip
  Downloading pip-26.0.1-py3-none-any.whl (1.8 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.8/1.8 MB 16.9 MB/s eta 0:00:00
Requirement already satisfied: setuptools in /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/envs/latest/lib/python3.13/site-packages (67.6.1)
Collecting setuptools
  Downloading setuptools-82.0.1-py3-none-any.whl (1.0 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 27.9 MB/s eta 0:00:00
Installing collected packages: setuptools, pip
  Attempting uninstall: setuptools
    Found existing installation: setuptools 67.6.1
    Uninstalling setuptools-67.6.1:
      Successfully uninstalled setuptools-67.6.1
  Attempting uninstall: pip
    Found existing installation: pip 23.1
    Uninstalling pip-23.1:
      Successfully uninstalled pip-23.1
Successfully installed pip-26.0.1 setuptools-82.0.1

[rtd-command-info] start-time: 2026-03-20T10:08:03.161414Z, end-time: 2026-03-20T10:08:04.994855Z, duration: 1, exit-code: 0
python -m pip install --upgrade --no-cache-dir mkdocs
Collecting mkdocs
  Downloading mkdocs-1.6.1-py3-none-any.whl.metadata (6.0 kB)
Collecting click>=7.0 (from mkdocs)
  Downloading click-8.3.1-py3-none-any.whl.metadata (2.6 kB)
Collecting ghp-import>=1.0 (from mkdocs)
  Downloading ghp_import-2.1.0-py3-none-any.whl.metadata (7.2 kB)
Collecting jinja2>=2.11.1 (from mkdocs)
  Downloading jinja2-3.1.6-py3-none-any.whl.metadata (2.9 kB)
Collecting markdown>=3.3.6 (from mkdocs)
  Downloading markdown-3.10.2-py3-none-any.whl.metadata (5.1 kB)
Collecting markupsafe>=2.0.1 (from mkdocs)
  Downloading markupsafe-3.0.3-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (2.7 kB)
Collecting mergedeep>=1.3.4 (from mkdocs)
  Downloading mergedeep-1.3.4-py3-none-any.whl.metadata (4.3 kB)
Collecting mkdocs-get-deps>=0.2.0 (from mkdocs)
  Downloading mkdocs_get_deps-0.2.2-py3-none-any.whl.metadata (4.0 kB)
Collecting packaging>=20.5 (from mkdocs)
  Downloading packaging-26.0-py3-none-any.whl.metadata (3.3 kB)
Collecting pathspec>=0.11.1 (from mkdocs)
  Downloading pathspec-1.0.4-py3-none-any.whl.metadata (13 kB)
Collecting pyyaml-env-tag>=0.1 (from mkdocs)
  Downloading pyyaml_env_tag-1.1-py3-none-any.whl.metadata (5.5 kB)
Collecting pyyaml>=5.1 (from mkdocs)
  Downloading pyyaml-6.0.3-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (2.4 kB)
Collecting watchdog>=2.0 (from mkdocs)
  Downloading watchdog-6.0.0-py3-none-manylinux2014_x86_64.whl.metadata (44 kB)
Collecting python-dateutil>=2.8.1 (from ghp-import>=1.0->mkdocs)
  Downloading python_dateutil-2.9.0.post0-py2.py3-none-any.whl.metadata (8.4 kB)
Collecting platformdirs>=2.2.0 (from mkdocs-get-deps>=0.2.0->mkdocs)
  Downloading platformdirs-4.9.4-py3-none-any.whl.metadata (4.7 kB)
Collecting six>=1.5 (from python-dateutil>=2.8.1->ghp-import>=1.0->mkdocs)
  Downloading six-1.17.0-py2.py3-none-any.whl.metadata (1.7 kB)
Downloading mkdocs-1.6.1-py3-none-any.whl (3.9 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.9/3.9 MB 66.1 MB/s  0:00:00
Downloading click-8.3.1-py3-none-any.whl (108 kB)
Downloading ghp_import-2.1.0-py3-none-any.whl (11 kB)
Downloading jinja2-3.1.6-py3-none-any.whl (134 kB)
Downloading markdown-3.10.2-py3-none-any.whl (108 kB)
Downloading markupsafe-3.0.3-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (22 kB)
Downloading mergedeep-1.3.4-py3-none-any.whl (6.4 kB)
Downloading mkdocs_get_deps-0.2.2-py3-none-any.whl (9.6 kB)
Downloading packaging-26.0-py3-none-any.whl (74 kB)
Downloading pathspec-1.0.4-py3-none-any.whl (55 kB)
Downloading platformdirs-4.9.4-py3-none-any.whl (21 kB)
Downloading python_dateutil-2.9.0.post0-py2.py3-none-any.whl (229 kB)
Downloading pyyaml-6.0.3-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (801 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 801.6/801.6 kB 922.2 MB/s  0:00:00
Downloading pyyaml_env_tag-1.1-py3-none-any.whl (4.7 kB)
Downloading six-1.17.0-py2.py3-none-any.whl (11 kB)
Downloading watchdog-6.0.0-py3-none-manylinux2014_x86_64.whl (79 kB)
Installing collected packages: watchdog, six, pyyaml, platformdirs, pathspec, packaging, mergedeep, markupsafe, markdown, click, pyyaml-env-tag, python-dateutil, mkdocs-get-deps, jinja2, ghp-import, mkdocs

Successfully installed click-8.3.1 ghp-import-2.1.0 jinja2-3.1.6 markdown-3.10.2 markupsafe-3.0.3 mergedeep-1.3.4 mkdocs-1.6.1 mkdocs-get-deps-0.2.2 packaging-26.0 pathspec-1.0.4 platformdirs-4.9.4 python-dateutil-2.9.0.post0 pyyaml-6.0.3 pyyaml-env-tag-1.1 six-1.17.0 watchdog-6.0.0

[rtd-command-info] start-time: 2026-03-20T10:08:05.039944Z, end-time: 2026-03-20T10:08:11.225435Z, duration: 6, exit-code: 0
python -m pip install --exists-action=w --no-cache-dir -r docs/en/requirements.txt
Collecting mkdocs-material==9.7.1 (from -r docs/en/requirements.txt (line 1))
  Downloading mkdocs_material-9.7.1-py3-none-any.whl.metadata (19 kB)
Collecting mkdocstrings==0.24.1 (from mkdocstrings[python]==0.24.1->-r docs/en/requirements.txt (line 2))
  Downloading mkdocstrings-0.24.1-py3-none-any.whl.metadata (7.6 kB)
Collecting mkdocs-static-i18n==1.3.1 (from -r docs/en/requirements.txt (line 3))
  Downloading mkdocs_static_i18n-1.3.1-py3-none-any.whl.metadata (4.1 kB)
Collecting babel>=2.10 (from mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1))
  Downloading babel-2.18.0-py3-none-any.whl.metadata (2.2 kB)
Collecting backrefs>=5.7.post1 (from mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1))
  Downloading backrefs-6.2-py313-none-any.whl.metadata (3.0 kB)
Collecting colorama>=0.4 (from mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1))
  Downloading colorama-0.4.6-py2.py3-none-any.whl.metadata (17 kB)
Requirement already satisfied: jinja2>=3.1 in /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/envs/latest/lib/python3.13/site-packages (from mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1)) (3.1.6)
Requirement already satisfied: markdown>=3.2 in /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/envs/latest/lib/python3.13/site-packages (from mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1)) (3.10.2)
Collecting mkdocs-material-extensions>=1.3 (from mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1))
  Downloading mkdocs_material_extensions-1.3.1-py3-none-any.whl.metadata (6.9 kB)
Requirement already satisfied: mkdocs>=1.6 in /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/envs/latest/lib/python3.13/site-packages (from mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1)) (1.6.1)
Collecting paginate>=0.5 (from mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1))
  Downloading paginate-0.5.7-py2.py3-none-any.whl.metadata (11 kB)
Collecting pygments>=2.16 (from mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1))
  Downloading pygments-2.19.2-py3-none-any.whl.metadata (2.5 kB)
Collecting pymdown-extensions>=10.2 (from mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1))
  Downloading pymdown_extensions-10.21-py3-none-any.whl.metadata (3.1 kB)
Collecting requests>=2.30 (from mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1))
  Downloading requests-2.32.5-py3-none-any.whl.metadata (4.9 kB)
Requirement already satisfied: click>=7.0 in /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/envs/latest/lib/python3.13/site-packages (from mkdocstrings==0.24.1->mkdocstrings[python]==0.24.1->-r docs/en/requirements.txt (line 2)) (8.3.1)
Requirement already satisfied: MarkupSafe>=1.1 in /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/envs/latest/lib/python3.13/site-packages (from mkdocstrings==0.24.1->mkdocstrings[python]==0.24.1->-r docs/en/requirements.txt (line 2)) (3.0.3)
Collecting mkdocs-autorefs>=0.3.1 (from mkdocstrings==0.24.1->mkdocstrings[python]==0.24.1->-r docs/en/requirements.txt (line 2))
  Downloading mkdocs_autorefs-1.4.4-py3-none-any.whl.metadata (14 kB)
Requirement already satisfied: platformdirs>=2.2.0 in /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/envs/latest/lib/python3.13/site-packages (from mkdocstrings==0.24.1->mkdocstrings[python]==0.24.1->-r docs/en/requirements.txt (line 2)) (4.9.4)
Collecting mkdocstrings-python>=0.5.2 (from mkdocstrings[python]==0.24.1->-r docs/en/requirements.txt (line 2))
  Downloading mkdocstrings_python-2.0.3-py3-none-any.whl.metadata (12 kB)
Requirement already satisfied: ghp-import>=1.0 in /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/envs/latest/lib/python3.13/site-packages (from mkdocs>=1.6->mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1)) (2.1.0)
Requirement already satisfied: mergedeep>=1.3.4 in /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/envs/latest/lib/python3.13/site-packages (from mkdocs>=1.6->mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1)) (1.3.4)
Requirement already satisfied: mkdocs-get-deps>=0.2.0 in /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/envs/latest/lib/python3.13/site-packages (from mkdocs>=1.6->mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1)) (0.2.2)
Requirement already satisfied: packaging>=20.5 in /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/envs/latest/lib/python3.13/site-packages (from mkdocs>=1.6->mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1)) (26.0)
Requirement already satisfied: pathspec>=0.11.1 in /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/envs/latest/lib/python3.13/site-packages (from mkdocs>=1.6->mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1)) (1.0.4)
Requirement already satisfied: pyyaml-env-tag>=0.1 in /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/envs/latest/lib/python3.13/site-packages (from mkdocs>=1.6->mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1)) (1.1)
Requirement already satisfied: pyyaml>=5.1 in /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/envs/latest/lib/python3.13/site-packages (from mkdocs>=1.6->mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1)) (6.0.3)
Requirement already satisfied: watchdog>=2.0 in /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/envs/latest/lib/python3.13/site-packages (from mkdocs>=1.6->mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1)) (6.0.0)
Requirement already satisfied: python-dateutil>=2.8.1 in /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/envs/latest/lib/python3.13/site-packages (from ghp-import>=1.0->mkdocs>=1.6->mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1)) (2.9.0.post0)
INFO: pip is looking at multiple versions of mkdocstrings-python to determine which version is compatible with other requirements. This could take a while.
  Downloading mkdocstrings_python-2.0.2-py3-none-any.whl.metadata (12 kB)
  Downloading mkdocstrings_python-2.0.1-py3-none-any.whl.metadata (13 kB)
  Downloading mkdocstrings_python-2.0.0-py3-none-any.whl.metadata (13 kB)
  Downloading mkdocstrings_python-1.19.0-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.18.2-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.18.1-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.18.0-py3-none-any.whl.metadata (5.6 kB)
INFO: pip is still looking at multiple versions of mkdocstrings-python to determine which version is compatible with other requirements. This could take a while.
  Downloading mkdocstrings_python-1.17.0-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.16.12-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.16.11-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.16.10-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.16.9-py3-none-any.whl.metadata (5.6 kB)
INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
  Downloading mkdocstrings_python-1.16.8-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.16.7-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.16.6-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.16.5-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.16.4-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.16.3-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.16.2-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.16.1-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.16.0-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.15.1-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.15.0-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.14.7-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.14.6-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.14.5-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.14.4-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.14.3-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.14.2-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.14.1-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.14.0-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.13.0-py3-none-any.whl.metadata (5.5 kB)
  Downloading mkdocstrings_python-1.12.2-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.12.1-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.12.0-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.11.1-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.11.0-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.10.9-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.10.8-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.10.7-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.10.6-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.10.5-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.10.4-py3-none-any.whl.metadata (5.6 kB)
  Downloading mkdocstrings_python-1.10.3-py3-none-any.whl.metadata (5.5 kB)
  Downloading mkdocstrings_python-1.10.2-py3-none-any.whl.metadata (5.5 kB)
  Downloading mkdocstrings_python-1.10.1-py3-none-any.whl.metadata (5.5 kB)
  Downloading mkdocstrings_python-1.10.0-py3-none-any.whl.metadata (5.5 kB)
  Downloading mkdocstrings_python-1.9.2-py3-none-any.whl.metadata (5.5 kB)
  Downloading mkdocstrings_python-1.9.1-py3-none-any.whl.metadata (5.5 kB)
Collecting markdown>=3.2 (from mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1))
  Downloading Markdown-3.5.2-py3-none-any.whl.metadata (7.0 kB)
Collecting griffe>=0.37 (from mkdocstrings-python>=0.5.2->mkdocstrings[python]==0.24.1->-r docs/en/requirements.txt (line 2))
  Downloading griffe-2.0.0-py3-none-any.whl.metadata (12 kB)
Collecting griffecli==2.0.0 (from griffe>=0.37->mkdocstrings-python>=0.5.2->mkdocstrings[python]==0.24.1->-r docs/en/requirements.txt (line 2))
  Downloading griffecli-2.0.0-py3-none-any.whl.metadata (1.2 kB)
Collecting griffelib==2.0.0 (from griffe>=0.37->mkdocstrings-python>=0.5.2->mkdocstrings[python]==0.24.1->-r docs/en/requirements.txt (line 2))
  Downloading griffelib-2.0.0-py3-none-any.whl.metadata (1.3 kB)
INFO: pip is looking at multiple versions of pymdown-extensions to determine which version is compatible with other requirements. This could take a while.
Collecting pymdown-extensions>=10.2 (from mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1))
  Downloading pymdown_extensions-10.20.1-py3-none-any.whl.metadata (3.1 kB)
  Downloading pymdown_extensions-10.20-py3-none-any.whl.metadata (3.1 kB)
  Downloading pymdown_extensions-10.19.1-py3-none-any.whl.metadata (3.1 kB)
  Downloading pymdown_extensions-10.19-py3-none-any.whl.metadata (3.1 kB)
  Downloading pymdown_extensions-10.18-py3-none-any.whl.metadata (3.1 kB)
  Downloading pymdown_extensions-10.17.2-py3-none-any.whl.metadata (3.1 kB)
  Downloading pymdown_extensions-10.17.1-py3-none-any.whl.metadata (3.1 kB)
INFO: pip is still looking at multiple versions of pymdown-extensions to determine which version is compatible with other requirements. This could take a while.
  Downloading pymdown_extensions-10.17-py3-none-any.whl.metadata (3.1 kB)
  Downloading pymdown_extensions-10.16.1-py3-none-any.whl.metadata (3.1 kB)
  Downloading pymdown_extensions-10.16-py3-none-any.whl.metadata (3.0 kB)
  Downloading pymdown_extensions-10.15-py3-none-any.whl.metadata (3.0 kB)
  Downloading pymdown_extensions-10.14.3-py3-none-any.whl.metadata (3.0 kB)
INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. See https://pip.pypa.io/warnings/backtracking for guidance. If you want to abort this run, press Ctrl + C.
  Downloading pymdown_extensions-10.14.2-py3-none-any.whl.metadata (3.0 kB)
  Downloading pymdown_extensions-10.14.1-py3-none-any.whl.metadata (3.0 kB)
  Downloading pymdown_extensions-10.14-py3-none-any.whl.metadata (3.0 kB)
  Downloading pymdown_extensions-10.13-py3-none-any.whl.metadata (3.0 kB)
  Downloading pymdown_extensions-10.12-py3-none-any.whl.metadata (3.0 kB)
  Downloading pymdown_extensions-10.11.2-py3-none-any.whl.metadata (3.0 kB)
  Downloading pymdown_extensions-10.11.1-py3-none-any.whl.metadata (3.0 kB)
  Downloading pymdown_extensions-10.11-py3-none-any.whl.metadata (3.0 kB)
  Downloading pymdown_extensions-10.10.2-py3-none-any.whl.metadata (3.0 kB)
  Downloading pymdown_extensions-10.10.1-py3-none-any.whl.metadata (3.0 kB)
  Downloading pymdown_extensions-10.10-py3-none-any.whl.metadata (3.0 kB)
  Downloading pymdown_extensions-10.9-py3-none-any.whl.metadata (3.0 kB)
  Downloading pymdown_extensions-10.8.1-py3-none-any.whl.metadata (3.0 kB)
  Downloading pymdown_extensions-10.8-py3-none-any.whl.metadata (3.0 kB)
  Downloading pymdown_extensions-10.7.1-py3-none-any.whl.metadata (3.0 kB)
Requirement already satisfied: six>=1.5 in /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/envs/latest/lib/python3.13/site-packages (from python-dateutil>=2.8.1->ghp-import>=1.0->mkdocs>=1.6->mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1)) (1.17.0)
Collecting charset_normalizer<4,>=2 (from requests>=2.30->mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1))
  Downloading charset_normalizer-3.4.6-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (40 kB)
Collecting idna<4,>=2.5 (from requests>=2.30->mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1))
  Downloading idna-3.11-py3-none-any.whl.metadata (8.4 kB)
Collecting urllib3<3,>=1.21.1 (from requests>=2.30->mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1))
  Downloading urllib3-2.6.3-py3-none-any.whl.metadata (6.9 kB)
Collecting certifi>=2017.4.17 (from requests>=2.30->mkdocs-material==9.7.1->-r docs/en/requirements.txt (line 1))
  Downloading certifi-2026.2.25-py3-none-any.whl.metadata (2.5 kB)
Downloading mkdocs_material-9.7.1-py3-none-any.whl (9.3 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.3/9.3 MB 125.6 MB/s  0:00:00
Downloading mkdocstrings-0.24.1-py3-none-any.whl (28 kB)
Downloading mkdocs_static_i18n-1.3.1-py3-none-any.whl (21 kB)
Downloading babel-2.18.0-py3-none-any.whl (10.2 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10.2/10.2 MB 482.1 MB/s  0:00:00
Downloading backrefs-6.2-py313-none-any.whl (400 kB)
Downloading colorama-0.4.6-py2.py3-none-any.whl (25 kB)
Downloading mkdocs_autorefs-1.4.4-py3-none-any.whl (25 kB)
Downloading mkdocs_material_extensions-1.3.1-py3-none-any.whl (8.7 kB)
Downloading mkdocstrings_python-1.9.1-py3-none-any.whl (58 kB)
Downloading Markdown-3.5.2-py3-none-any.whl (103 kB)
Downloading griffe-2.0.0-py3-none-any.whl (5.2 kB)
Downloading griffecli-2.0.0-py3-none-any.whl (9.3 kB)
Downloading griffelib-2.0.0-py3-none-any.whl (142 kB)
Downloading paginate-0.5.7-py2.py3-none-any.whl (13 kB)
Downloading pygments-2.19.2-py3-none-any.whl (1.2 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2/1.2 MB 1.0 GB/s  0:00:00
Downloading pymdown_extensions-10.7.1-py3-none-any.whl (250 kB)
Downloading requests-2.32.5-py3-none-any.whl (64 kB)
Downloading charset_normalizer-3.4.6-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (206 kB)
Downloading idna-3.11-py3-none-any.whl (71 kB)
Downloading urllib3-2.6.3-py3-none-any.whl (131 kB)
Downloading certifi-2026.2.25-py3-none-any.whl (153 kB)
Installing collected packages: paginate, urllib3, pygments, mkdocs-material-extensions, markdown, idna, griffelib, colorama, charset_normalizer, certifi, backrefs, babel, requests, pymdown-extensions, griffecli, griffe, mkdocs-static-i18n, mkdocs-material, mkdocs-autorefs, mkdocstrings, mkdocstrings-python
  Attempting uninstall: markdown
    Found existing installation: Markdown 3.10.2
    Uninstalling Markdown-3.10.2:
      Successfully uninstalled Markdown-3.10.2

Successfully installed babel-2.18.0 backrefs-6.2 certifi-2026.2.25 charset_normalizer-3.4.6 colorama-0.4.6 griffe-2.0.0 griffecli-2.0.0 griffelib-2.0.0 idna-3.11 markdown-3.5.2 mkdocs-autorefs-1.4.4 mkdocs-material-9.7.1 mkdocs-material-extensions-1.3.1 mkdocs-static-i18n-1.3.1 mkdocstrings-0.24.1 mkdocstrings-python-1.9.1 paginate-0.5.7 pygments-2.19.2 pymdown-extensions-10.7.1 requests-2.32.5 urllib3-2.6.3

[rtd-command-info] start-time: 2026-03-20T10:08:11.323213Z, end-time: 2026-03-20T10:08:11.366956Z, duration: 0, exit-code: 0
cat mkdocs.yml
site_name: Tenxyte Documentation
site_url: https://tenxyte.readthedocs.io/
repo_url: https://github.com/tenxyte/tenxyte
repo_name: tenxyte/tenxyte
docs_dir: docs

theme:
  name: material
  logo: https://tenxyte-graphics.s3.us-east-1.amazonaws.com/tenxyte-graphics/out/custom/SVG/v1_logo-sharp.svg
  favicon: https://tenxyte-graphics.s3.us-east-1.amazonaws.com/tenxyte-graphics/out/custom/SVG/v1_logo-sharp.svg
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - search.suggest
    - search.highlight

extra:
  # Configuration des langues pour Material
  alternate:
    - name: English
      link: /en/
      lang: en
    - name: Français
      link: /fr/
      lang: fr
  social:
    - icon: fontawesome/brands/github
      link: https://github.com/tenxyte/tenxyte

plugins:
  - search:
      lang:
        - en
        - fr
  
  - i18n:  # Plugin multilangue
      default_language: en
      languages:
        - locale: en
          name: English
          default: true
          build: true
          site_name: "Tenxyte Documentation"
        - locale: fr
          name: Français
          build: true
          site_name: "Documentation Tenxyte"
      material_alternate: true  # Active le sélecteur de langue dans Material
      nav_translations:
        fr:
          Getting Started: Démarrage
          Architecture: Architecture
          API Reference: Référence API
          Features: Fonctionnalités
          Operations & Maintenance: Opérations & Maintenance
          Runbooks: Guides d'Opération
          Settings Reference: Référence des Paramètres
          Quickstart: Démarrage Rapide
          FastAPI Quickstart: Démarrage Rapide FastAPI
          Architecture Guide: Guide d'Architecture
          Custom Adapters: Adaptateurs Personnalisés
          Async Guide: Guide Asynchrone
          API Endpoints: Points d'Accès API
          Data Schemas: Schémas de Données
          AIRs Reference: Référence AIRs
          Admin Accounts: Comptes Administrateur
          Applications Guide: Guide des Applications
          Organizations: Organisations
          RBAC Guide: Guide RBAC
          Security Guide: Guide de Sécurité
          Task Service: Service de Tâches
          Periodic Tasks: Tâches Périodiques
          Troubleshooting: Dépannage
          Migration Guide: Guide de Migration
          Deployment: Déploiement
          Incident Response: Réponse aux Incidents
          Rollback: Rollback
          Contributing: Contribution
          Contributing Guidelines: Guide de Contribution
          Testing: Tests
 
markdown_extensions:
  - pymdownx.highlight:
      anchor_linenums: true
      line_spans: __span
      pygments_lang_class: true
  - pymdownx.inlinehilite
  - pymdownx.snippets
  - pymdownx.superfences
  - tables
  - admonition
  - pymdownx.emoji:
      emoji_index: !!python/name:material.extensions.emoji.twemoji
      emoji_generator: !!python/name:material.extensions.emoji.to_svg
  - pymdownx.tabbed:
      alternate_style: true

nav:
  - Home:
      en: en/README.md
      fr: fr/README.md
  - 'Getting Started':
      - 'Quickstart':
          en: en/quickstart.md
          fr: fr/quickstart.md
      - 'FastAPI Quickstart':
          en: en/fastapi_quickstart.md
          fr: fr/fastapi_quickstart.md
      - 'Settings Reference':
          en: en/settings.md
          fr: fr/settings.md
  - 'Architecture':
      - 'Architecture Guide':
          en: en/architecture.md
          fr: fr/architecture.md
      - 'Custom Adapters':
          en: en/custom_adapters.md
          fr: fr/custom_adapters.md
      - 'Async Guide':
          en: en/async_guide.md
          fr: fr/async_guide.md
  - 'API Reference':
      - 'API Endpoints':
          en: en/endpoints.md
          fr: fr/endpoints.md
      - 'Data Schemas':
          en: en/schemas.md
          fr: fr/schemas.md
      - 'AIRs Reference':
          en: en/airs.md
          fr: fr/airs.md
  - 'Features':
      - 'Admin Accounts':
          en: en/admin.md
          fr: fr/admin.md
      - 'Applications Guide':
          en: en/applications.md
          fr: fr/applications.md
      - 'Organizations':
          en: en/organizations.md
          fr: fr/organizations.md
      - 'RBAC Guide':
          en: en/rbac.md
          fr: fr/rbac.md
      - 'Security Guide':
          en: en/security.md
          fr: fr/security.md
      - 'Task Service':
          en: en/task_service.md
          fr: fr/task_service.md
  - 'Operations & Maintenance':
      - 'Periodic Tasks':
          en: en/periodic_tasks.md
          fr: fr/periodic_tasks.md
      - 'Troubleshooting':
          en: en/troubleshooting.md
          fr: fr/troubleshooting.md
      - 'Migration Guide':
          en: en/MIGRATION_GUIDE.md
          fr: fr/MIGRATION_GUIDE.md
      - 'Runbooks':
          - 'Deployment':
              en: en/runbooks/deployment.md
              fr: fr/runbooks/deployment.md
          - 'Incident Response':
              en: en/runbooks/incident_response.md
              fr: fr/runbooks/incident_response.md
          - 'Rollback':
              en: en/runbooks/rollback.md
              fr: fr/runbooks/rollback.md
  - 'Contributing':
      - 'Contributing Guidelines':
          en: en/CONTRIBUTING.md
          fr: fr/CONTRIBUTING.md
      - 'Testing':
          en: en/TESTING.md
          fr: fr/TESTING.md

[rtd-command-info] start-time: 2026-03-20T10:08:11.411639Z, end-time: 2026-03-20T10:08:17.297284Z, duration: 5, exit-code: 0
python -m mkdocs build --clean --site-dir $READTHEDOCS_OUTPUT/html --config-file mkdocs.yml
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'nav': Expected nav to be a list, got dict with keys ('en', 'fr')
WARNING -  Config value 'plugins': Plugin 'i18n' option 'nav_translations': Unrecognised configuration name: nav_translations
WARNING -  Config value 'plugins': Plugin 'i18n' option 'material_alternate': Unrecognised configuration name: material_alternate
WARNING -  Config value 'plugins': Plugin 'i18n' option 'default_language': Unrecognised configuration name: default_language
INFO    -  mkdocs_static_i18n: Building 'en' documentation to directory: /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/checkouts/latest/_readthedocs/html
INFO    -  mkdocs_static_i18n: Overriding 'en' config 'site_name' with 'Tenxyte Documentation'
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/checkouts/latest/_readthedocs/html
WARNING -  Doc file 'en/README.md' contains a link '../docs_site/index.html', but the target 'docs_site/index.html' is not found among documentation files.
WARNING -  Doc file 'en/README.md' contains a link '../../tenxyte_api_collection.postman_collection.json', but the target '../tenxyte_api_collection.postman_collection.json' is not found among documentation files.
INFO    -  Doc file 'en/README.md' contains an unrecognized relative link '../../LICENSE', it was left as is.
WARNING -  Doc file 'en/README.md' contains a link '../../CHANGELOG.md', but the target '../CHANGELOG.md' is not found among documentation files.
WARNING -  Doc file 'en/CONTRIBUTING.md' contains a link '../../src/tenxyte/core/schemas.py', but the target '../src/tenxyte/core/schemas.py' is not found among documentation files.
WARNING -  Doc file 'fr/CONTRIBUTING.md' contains a link '../../src/tenxyte/core/schemas.py', but the target '../src/tenxyte/core/schemas.py' is not found among documentation files.
INFO    -  Doc file 'en/README.md' contains a link '#quickstart--development', but there is no such anchor on this page.
INFO    -  Doc file 'en/README.md' contains a link '#request--response-examples', but there is no such anchor on this page.
INFO    -  Doc file 'en/README.md' contains a link '#endpoints--documentation', but there is no such anchor on this page.
INFO    -  Doc file 'en/README.md' contains a link '#-documentation-structure', but there is no such anchor on this page.
INFO    -  Doc file 'en/README.md' contains a link '#architecture-core--adapters', but there is no such anchor on this page.
INFO    -  Doc file 'en/README.md' contains a link '#customization--extension', but there is no such anchor on this page.
INFO    -  Doc file 'en/README.md' contains a link '#development--testing', but there is no such anchor on this page.
INFO    -  Doc file 'en/README.md' contains a link '#frequently-asked-questions--troubleshooting', but there is no such anchor on this page.
INFO    -  Doc file 'en/README.md' contains a link '#mongodb--django-admin-support', but there is no such anchor on this page.
INFO    -  Doc file 'en/MIGRATION_GUIDE.md' contains a link '#step-1--preserve-existing-users', but there is no such anchor on this page.
INFO    -  Doc file 'en/MIGRATION_GUIDE.md' contains a link '#step-2--migrate-roles-and-permissions', but there is no such anchor on this page.
INFO    -  Doc file 'en/MIGRATION_GUIDE.md' contains a link '#step-3--update-frontend-headers', but there is no such anchor on this page.
INFO    -  Doc file 'en/admin.md' contains a link '#creation-1', but there is no such anchor on this page.
INFO    -  Doc file 'en/admin.md' contains a link '#capabilities-1', but there is no such anchor on this page.
INFO    -  Doc file 'en/airs.md' contains a link '#1-core-agentic-parity--agenttoken', but there is no such anchor on this page.
INFO    -  Doc file 'en/airs.md' contains a link '#2-circuit-breaker--rate-limiting', but there is no such anchor on this page.
INFO    -  Doc file 'en/airs.md' contains a link '#4-guardrails-pii-redaction--budget-tracking', but there is no such anchor on this page.
INFO    -  Doc file 'en/endpoints.md' contains a link '#patch-organizationsmembersuserid-orgmembersmanage', but there is no such anchor on this page.
INFO    -  Doc file 'en/endpoints.md' contains a link '#delete-organizationsmembersuseridremove-orgmembersremove', but there is no such anchor on this page.
INFO    -  Doc file 'en/periodic_tasks.md' contains a link '#usage--options', but there is no such anchor on this page.
INFO    -  Doc file 'en/periodic_tasks.md' contains a link '#3-monthly--security-tasks', but there is no such anchor on this page.
INFO    -  Doc file 'en/quickstart.md' contains a link '#-ready', but there is no such anchor on this page.
INFO    -  Doc file 'en/quickstart.md' contains a link '#4-login--use-your-jwt', but there is no such anchor on this page.
INFO    -  Doc file 'en/quickstart.md' contains a link '#mongodb--required-configuration', but there is no such anchor on this page.
INFO    -  Doc file 'en/rbac.md' contains a link '#permissions-1', but there is no such anchor on this page.
INFO    -  Doc file 'en/rbac.md' contains a link '#roles-1', but there is no such anchor on this page.
INFO    -  Doc file 'en/rbac.md' contains a link '#user-roles--permissions', but there is no such anchor on this page.
INFO    -  Doc file 'en/rbac.md' contains a link '#seeding--customization', but there is no such anchor on this page.
INFO    -  Doc file 'en/schemas.md' contains a link 'security.md#session--device-limits', but the doc 'en/security.md' does not contain an anchor '#session--device-limits'.
INFO    -  Doc file 'en/security.md' contains a link '#two-factor-authentication-2fa--totp', but there is no such anchor on this page.
INFO    -  Doc file 'en/security.md' contains a link '#session--device-limits', but there is no such anchor on this page.
INFO    -  Doc file 'en/settings.md' contains a link '#settings-priority', but there is no such anchor on this page.
INFO    -  Doc file 'en/settings.md' contains a link '#otp-email--sms-verification', but there is no such anchor on this page.
INFO    -  Doc file 'en/settings.md' contains a link '#rate-limiting--account-lockout', but there is no such anchor on this page.
INFO    -  Doc file 'en/settings.md' contains a link '#session--device-limits', but there is no such anchor on this page.
INFO    -  Doc file 'en/settings.md' contains a link '#webauthn--passkeys-fido2', but there is no such anchor on this page.
INFO    -  Doc file 'en/troubleshooting.md' contains a link 'periodic_tasks.md#7-encryption-key-rotation-field_encryption_key', but the doc 'en/periodic_tasks.md' does not contain an anchor '#7-encryption-key-rotation-field_encryption_key'.
INFO    -  Doc file 'fr/README.md' contains a link '#-structure-de-la-documentation', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#-aperçu-des-fonctionnalités-avancées', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#-mesures-de-qualité-de-la-documentation', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#️-scripts-de-documentation', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#-démarrage-rapide', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#-accès-à-la-documentation', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#-documentation-des-fonctionnalités-clés', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#-documentation-des-tests', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#-support-et-contribution', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#-normes-de-documentation', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#-résumé', but there is no such anchor on this page.
INFO    -  Doc file 'fr/CONTRIBUTING.md' contains a link '#configuration-du-développement', but there is no such anchor on this page.
INFO    -  Doc file 'fr/CONTRIBUTING.md' contains a link '#exécution-des-tests', but there is no such anchor on this page.
INFO    -  Doc file 'fr/CONTRIBUTING.md' contains a link '#signaler-des-problèmes', but there is no such anchor on this page.
INFO    -  Doc file 'fr/CONTRIBUTING.md' contains a link '#versions-supportées', but there is no such anchor on this page.
INFO    -  Doc file 'fr/CONTRIBUTING.md' contains a link '#code-of-conduct', but there is no such anchor on this page.
INFO    -  Doc file 'fr/CONTRIBUTING.md' contains a link '#questions', but there is no such anchor on this page.
INFO    -  Doc file 'fr/MIGRATION_GUIDE.md' contains a link '#migration-de-tenxyte-v09x-vers-v093-rearchitecture-du-coeur', but there is no such anchor on this page.
INFO    -  Doc file 'fr/MIGRATION_GUIDE.md' contains a link '#etape-1--preserver-les-utilisateurs-existants', but there is no such anchor on this page.
INFO    -  Doc file 'fr/MIGRATION_GUIDE.md' contains a link '#etape-2--migrer-les-roles-et-permissions', but there is no such anchor on this page.
INFO    -  Doc file 'fr/MIGRATION_GUIDE.md' contains a link '#etape-3--mettre-a-jour-les-en-tetes-du-frontend', but there is no such anchor on this page.
INFO    -  Doc file 'fr/admin.md' contains a link '#présentation', but there is no such anchor on this page.
INFO    -  Doc file 'fr/admin.md' contains a link '#création', but there is no such anchor on this page.
INFO    -  Doc file 'fr/admin.md' contains a link '#capacités', but there is no such anchor on this page.
INFO    -  Doc file 'fr/admin.md' contains a link '#2-rôles-dadministration-rbac', but there is no such anchor on this page.
INFO    -  Doc file 'fr/admin.md' contains a link '#création-1', but there is no such anchor on this page.
INFO    -  Doc file 'fr/admin.md' contains a link '#capacités-1', but there is no such anchor on this page.
INFO    -  Doc file 'fr/airs.md' contains a link '#présentation', but there is no such anchor on this page.
INFO    -  Doc file 'fr/airs.md' contains a link '#1-parité-agentique-de-base--agenttoken', but there is no such anchor on this page.
INFO    -  Doc file 'fr/airs.md' contains a link '#2-disjoncteur-et-limitation-de-débit', but there is no such anchor on this page.
INFO    -  Doc file 'fr/airs.md' contains a link '#3-intervention-humaine-human-in-the-loop---hitl', but there is no such anchor on this page.
INFO    -  Doc file 'fr/airs.md' contains a link '#4-garde-fous--caviardage-des-pii-et-suivi-budgétaire', but there is no such anchor on this page.
INFO    -  Doc file 'fr/airs.md' contains a link '#référence-de-configuration', but there is no such anchor on this page.
INFO    -  Doc file 'fr/applications.md' contains a link '#présentation', but there is no such anchor on this page.
INFO    -  Doc file 'fr/applications.md' contains a link '#créer-une-application', but there is no such anchor on this page.
INFO    -  Doc file 'fr/applications.md' contains a link '#obtenir-les-détails-dune-application', but there is no such anchor on this page.
INFO    -  Doc file 'fr/applications.md' contains a link '#mettre-à-jour-une-application', but there is no such anchor on this page.
INFO    -  Doc file 'fr/applications.md' contains a link '#régénérer-les-identifiants', but there is no such anchor on this page.
INFO    -  Doc file 'fr/applications.md' contains a link '#notes-de-sécurité', but there is no such anchor on this page.
INFO    -  Doc file 'fr/applications.md' contains a link '#modèle-de-données', but there is no such anchor on this page.
INFO    -  Doc file 'fr/async_guide.md' contains a link '#présentation', but there is no such anchor on this page.
INFO    -  Doc file 'fr/async_guide.md' contains a link '#référence-des-méthodes-asynchrones', but there is no such anchor on this page.
INFO    -  Doc file 'fr/async_guide.md' contains a link '#modèles-spécifiques-aux-frameworks', but there is no such anchor on this page.
INFO    -  Doc file 'fr/async_guide.md' contains a link '#considérations-de-performance', but there is no such anchor on this page.
INFO    -  Doc file 'fr/async_guide.md' contains a link '#pièges-courants', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#référence-des-points-de-terminaison', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#vérification-otp', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#authentification-à-deux-facteurs-2fa', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#rbac--permissions', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#rbac--rôles', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#rbac--rôles-et-permissions-utilisateur', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#admin--gestion-des-utilisateurs', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#admin--sécurité', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#admin--rgpd', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#utilisateur--rgpd', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#organisations-optionnel', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#patch-organizationsmembersuserid-orgmembersmanage', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#delete-organizationsmembersuseridremove-orgmembersremove', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#webauthn--passkeys-fido2', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#légende', but there is no such anchor on this page.
INFO    -  Doc file 'fr/periodic_tasks.md' contains a link '#2-surveillance-des-battements-de-coeur-des-agents-heartbeats', but there is no such anchor on this page.
INFO    -  Doc file 'fr/periodic_tasks.md' contains a link '#3-taches-mensuelles--de-securite', but there is no such anchor on this page.
INFO    -  Doc file 'fr/quickstart.md' contains a link '#2-configuration-settingspy', but there is no such anchor on this page.
INFO    -  Doc file 'fr/quickstart.md' contains a link '#-pret', but there is no such anchor on this page.
INFO    -  Doc file 'fr/quickstart.md' contains a link '#4-connexion--utilisation-de-votre-jwt', but there is no such anchor on this page.
INFO    -  Doc file 'fr/quickstart.md' contains a link '#mongodb--required-configuration', but there is no such anchor on this page.
INFO    -  Doc file 'fr/rbac.md' contains a link '#permissions-1', but there is no such anchor on this page.
INFO    -  Doc file 'fr/rbac.md' contains a link '#roles-1', but there is no such anchor on this page.
INFO    -  Doc file 'fr/schemas.md' contains a link '#réponse-derreur', but there is no such anchor on this page.
INFO    -  Doc file 'fr/schemas.md' contains a link '#réponse-paginée', but there is no such anchor on this page.
INFO    -  Doc file 'fr/schemas.md' contains a link '#rôle', but there is no such anchor on this page.
INFO    -  Doc file 'fr/schemas.md' contains a link 'security.md#audit-logging', but the doc 'fr/security.md' does not contain an anchor '#audit-logging'.
INFO    -  Doc file 'fr/schemas.md' contains a link 'security.md#session--device-limits', but the doc 'fr/security.md' does not contain an anchor '#session--device-limits'.
INFO    -  Doc file 'fr/security.md' contains a link '#authentification-a-deux-facteurs-2fa--totp', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#shortcut-secure-mode', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#core-settings', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#two-factor-authentication-totp', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#otp-email--sms-verification', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#password-policy', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#rate-limiting--account-lockout', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#session--device-limits', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#security-headers', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#social-login-oauth2', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#webauthn--passkeys-fido2', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#breach-password-check-haveibeenpwned', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#magic-link-passwordless', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#sms-backends', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#email-backends', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#audit-logging', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#organizations-b2b', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#swappable-models', but there is no such anchor on this page.
INFO    -  Doc file 'fr/troubleshooting.md' contains a link 'periodic_tasks.md#7-encryption-key-rotation-field_encryption_key', but the doc 'fr/periodic_tasks.md' does not contain an anchor '#7-encryption-key-rotation-field_encryption_key'.
INFO    -  mkdocs_static_i18n: Building 'fr' documentation to directory: /home/docs/checkouts/readthedocs.org/user_builds/tenxyte/checkouts/latest/_readthedocs/html/fr
INFO    -  mkdocs_static_i18n: Overriding 'fr' config 'site_name' with 'Documentation Tenxyte'
WARNING -  mkdocs_static_i18n: Could not find a homepage for locale 'fr'
WARNING -  Doc file 'en/README.md' contains a link '../docs_site/index.html', but the target 'docs_site/index.html' is not found among documentation files.
WARNING -  Doc file 'en/README.md' contains a link '../../tenxyte_api_collection.postman_collection.json', but the target '../tenxyte_api_collection.postman_collection.json' is not found among documentation files.
INFO    -  Doc file 'en/README.md' contains an unrecognized relative link '../../LICENSE', it was left as is.
WARNING -  Doc file 'en/README.md' contains a link '../../CHANGELOG.md', but the target '../CHANGELOG.md' is not found among documentation files.
WARNING -  Doc file 'en/CONTRIBUTING.md' contains a link '../../src/tenxyte/core/schemas.py', but the target '../src/tenxyte/core/schemas.py' is not found among documentation files.
WARNING -  Doc file 'fr/CONTRIBUTING.md' contains a link '../../src/tenxyte/core/schemas.py', but the target '../src/tenxyte/core/schemas.py' is not found among documentation files.
INFO    -  Doc file 'en/README.md' contains a link '#quickstart--development', but there is no such anchor on this page.
INFO    -  Doc file 'en/README.md' contains a link '#request--response-examples', but there is no such anchor on this page.
INFO    -  Doc file 'en/README.md' contains a link '#endpoints--documentation', but there is no such anchor on this page.
INFO    -  Doc file 'en/README.md' contains a link '#-documentation-structure', but there is no such anchor on this page.
INFO    -  Doc file 'en/README.md' contains a link '#architecture-core--adapters', but there is no such anchor on this page.
INFO    -  Doc file 'en/README.md' contains a link '#customization--extension', but there is no such anchor on this page.
INFO    -  Doc file 'en/README.md' contains a link '#development--testing', but there is no such anchor on this page.
INFO    -  Doc file 'en/README.md' contains a link '#frequently-asked-questions--troubleshooting', but there is no such anchor on this page.
INFO    -  Doc file 'en/README.md' contains a link '#mongodb--django-admin-support', but there is no such anchor on this page.
INFO    -  Doc file 'en/MIGRATION_GUIDE.md' contains a link '#step-1--preserve-existing-users', but there is no such anchor on this page.
INFO    -  Doc file 'en/MIGRATION_GUIDE.md' contains a link '#step-2--migrate-roles-and-permissions', but there is no such anchor on this page.
INFO    -  Doc file 'en/MIGRATION_GUIDE.md' contains a link '#step-3--update-frontend-headers', but there is no such anchor on this page.
INFO    -  Doc file 'en/admin.md' contains a link '#creation-1', but there is no such anchor on this page.
INFO    -  Doc file 'en/admin.md' contains a link '#capabilities-1', but there is no such anchor on this page.
INFO    -  Doc file 'en/airs.md' contains a link '#1-core-agentic-parity--agenttoken', but there is no such anchor on this page.
INFO    -  Doc file 'en/airs.md' contains a link '#2-circuit-breaker--rate-limiting', but there is no such anchor on this page.
INFO    -  Doc file 'en/airs.md' contains a link '#4-guardrails-pii-redaction--budget-tracking', but there is no such anchor on this page.
INFO    -  Doc file 'en/endpoints.md' contains a link '#patch-organizationsmembersuserid-orgmembersmanage', but there is no such anchor on this page.
INFO    -  Doc file 'en/endpoints.md' contains a link '#delete-organizationsmembersuseridremove-orgmembersremove', but there is no such anchor on this page.
INFO    -  Doc file 'en/periodic_tasks.md' contains a link '#usage--options', but there is no such anchor on this page.
INFO    -  Doc file 'en/periodic_tasks.md' contains a link '#3-monthly--security-tasks', but there is no such anchor on this page.
INFO    -  Doc file 'en/quickstart.md' contains a link '#-ready', but there is no such anchor on this page.
INFO    -  Doc file 'en/quickstart.md' contains a link '#4-login--use-your-jwt', but there is no such anchor on this page.
INFO    -  Doc file 'en/quickstart.md' contains a link '#mongodb--required-configuration', but there is no such anchor on this page.
INFO    -  Doc file 'en/rbac.md' contains a link '#permissions-1', but there is no such anchor on this page.
INFO    -  Doc file 'en/rbac.md' contains a link '#roles-1', but there is no such anchor on this page.
INFO    -  Doc file 'en/rbac.md' contains a link '#user-roles--permissions', but there is no such anchor on this page.
INFO    -  Doc file 'en/rbac.md' contains a link '#seeding--customization', but there is no such anchor on this page.
INFO    -  Doc file 'en/schemas.md' contains a link 'security.md#session--device-limits', but the doc 'en/security.md' does not contain an anchor '#session--device-limits'.
INFO    -  Doc file 'en/security.md' contains a link '#two-factor-authentication-2fa--totp', but there is no such anchor on this page.
INFO    -  Doc file 'en/security.md' contains a link '#session--device-limits', but there is no such anchor on this page.
INFO    -  Doc file 'en/settings.md' contains a link '#settings-priority', but there is no such anchor on this page.
INFO    -  Doc file 'en/settings.md' contains a link '#otp-email--sms-verification', but there is no such anchor on this page.
INFO    -  Doc file 'en/settings.md' contains a link '#rate-limiting--account-lockout', but there is no such anchor on this page.
INFO    -  Doc file 'en/settings.md' contains a link '#session--device-limits', but there is no such anchor on this page.
INFO    -  Doc file 'en/settings.md' contains a link '#webauthn--passkeys-fido2', but there is no such anchor on this page.
INFO    -  Doc file 'en/troubleshooting.md' contains a link 'periodic_tasks.md#7-encryption-key-rotation-field_encryption_key', but the doc 'en/periodic_tasks.md' does not contain an anchor '#7-encryption-key-rotation-field_encryption_key'.
INFO    -  Doc file 'fr/README.md' contains a link '#-structure-de-la-documentation', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#-aperçu-des-fonctionnalités-avancées', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#-mesures-de-qualité-de-la-documentation', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#️-scripts-de-documentation', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#-démarrage-rapide', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#-accès-à-la-documentation', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#-documentation-des-fonctionnalités-clés', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#-documentation-des-tests', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#-support-et-contribution', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#-normes-de-documentation', but there is no such anchor on this page.
INFO    -  Doc file 'fr/README.md' contains a link '#-résumé', but there is no such anchor on this page.
INFO    -  Doc file 'fr/CONTRIBUTING.md' contains a link '#configuration-du-développement', but there is no such anchor on this page.
INFO    -  Doc file 'fr/CONTRIBUTING.md' contains a link '#exécution-des-tests', but there is no such anchor on this page.
INFO    -  Doc file 'fr/CONTRIBUTING.md' contains a link '#signaler-des-problèmes', but there is no such anchor on this page.
INFO    -  Doc file 'fr/CONTRIBUTING.md' contains a link '#versions-supportées', but there is no such anchor on this page.
INFO    -  Doc file 'fr/CONTRIBUTING.md' contains a link '#code-of-conduct', but there is no such anchor on this page.
INFO    -  Doc file 'fr/CONTRIBUTING.md' contains a link '#questions', but there is no such anchor on this page.
INFO    -  Doc file 'fr/MIGRATION_GUIDE.md' contains a link '#migration-de-tenxyte-v09x-vers-v093-rearchitecture-du-coeur', but there is no such anchor on this page.
INFO    -  Doc file 'fr/MIGRATION_GUIDE.md' contains a link '#etape-1--preserver-les-utilisateurs-existants', but there is no such anchor on this page.
INFO    -  Doc file 'fr/MIGRATION_GUIDE.md' contains a link '#etape-2--migrer-les-roles-et-permissions', but there is no such anchor on this page.
INFO    -  Doc file 'fr/MIGRATION_GUIDE.md' contains a link '#etape-3--mettre-a-jour-les-en-tetes-du-frontend', but there is no such anchor on this page.
INFO    -  Doc file 'fr/admin.md' contains a link '#présentation', but there is no such anchor on this page.
INFO    -  Doc file 'fr/admin.md' contains a link '#création', but there is no such anchor on this page.
INFO    -  Doc file 'fr/admin.md' contains a link '#capacités', but there is no such anchor on this page.
INFO    -  Doc file 'fr/admin.md' contains a link '#2-rôles-dadministration-rbac', but there is no such anchor on this page.
INFO    -  Doc file 'fr/admin.md' contains a link '#création-1', but there is no such anchor on this page.
INFO    -  Doc file 'fr/admin.md' contains a link '#capacités-1', but there is no such anchor on this page.
INFO    -  Doc file 'fr/airs.md' contains a link '#présentation', but there is no such anchor on this page.
INFO    -  Doc file 'fr/airs.md' contains a link '#1-parité-agentique-de-base--agenttoken', but there is no such anchor on this page.
INFO    -  Doc file 'fr/airs.md' contains a link '#2-disjoncteur-et-limitation-de-débit', but there is no such anchor on this page.
INFO    -  Doc file 'fr/airs.md' contains a link '#3-intervention-humaine-human-in-the-loop---hitl', but there is no such anchor on this page.
INFO    -  Doc file 'fr/airs.md' contains a link '#4-garde-fous--caviardage-des-pii-et-suivi-budgétaire', but there is no such anchor on this page.
INFO    -  Doc file 'fr/airs.md' contains a link '#référence-de-configuration', but there is no such anchor on this page.
INFO    -  Doc file 'fr/applications.md' contains a link '#présentation', but there is no such anchor on this page.
INFO    -  Doc file 'fr/applications.md' contains a link '#créer-une-application', but there is no such anchor on this page.
INFO    -  Doc file 'fr/applications.md' contains a link '#obtenir-les-détails-dune-application', but there is no such anchor on this page.
INFO    -  Doc file 'fr/applications.md' contains a link '#mettre-à-jour-une-application', but there is no such anchor on this page.
INFO    -  Doc file 'fr/applications.md' contains a link '#régénérer-les-identifiants', but there is no such anchor on this page.
INFO    -  Doc file 'fr/applications.md' contains a link '#notes-de-sécurité', but there is no such anchor on this page.
INFO    -  Doc file 'fr/applications.md' contains a link '#modèle-de-données', but there is no such anchor on this page.
INFO    -  Doc file 'fr/async_guide.md' contains a link '#présentation', but there is no such anchor on this page.
INFO    -  Doc file 'fr/async_guide.md' contains a link '#référence-des-méthodes-asynchrones', but there is no such anchor on this page.
INFO    -  Doc file 'fr/async_guide.md' contains a link '#modèles-spécifiques-aux-frameworks', but there is no such anchor on this page.
INFO    -  Doc file 'fr/async_guide.md' contains a link '#considérations-de-performance', but there is no such anchor on this page.
INFO    -  Doc file 'fr/async_guide.md' contains a link '#pièges-courants', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#référence-des-points-de-terminaison', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#vérification-otp', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#authentification-à-deux-facteurs-2fa', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#rbac--permissions', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#rbac--rôles', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#rbac--rôles-et-permissions-utilisateur', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#admin--gestion-des-utilisateurs', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#admin--sécurité', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#admin--rgpd', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#utilisateur--rgpd', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#organisations-optionnel', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#patch-organizationsmembersuserid-orgmembersmanage', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#delete-organizationsmembersuseridremove-orgmembersremove', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#webauthn--passkeys-fido2', but there is no such anchor on this page.
INFO    -  Doc file 'fr/endpoints.md' contains a link '#légende', but there is no such anchor on this page.
INFO    -  Doc file 'fr/periodic_tasks.md' contains a link '#2-surveillance-des-battements-de-coeur-des-agents-heartbeats', but there is no such anchor on this page.
INFO    -  Doc file 'fr/periodic_tasks.md' contains a link '#3-taches-mensuelles--de-securite', but there is no such anchor on this page.
INFO    -  Doc file 'fr/quickstart.md' contains a link '#2-configuration-settingspy', but there is no such anchor on this page.
INFO    -  Doc file 'fr/quickstart.md' contains a link '#-pret', but there is no such anchor on this page.
INFO    -  Doc file 'fr/quickstart.md' contains a link '#4-connexion--utilisation-de-votre-jwt', but there is no such anchor on this page.
INFO    -  Doc file 'fr/quickstart.md' contains a link '#mongodb--required-configuration', but there is no such anchor on this page.
INFO    -  Doc file 'fr/rbac.md' contains a link '#permissions-1', but there is no such anchor on this page.
INFO    -  Doc file 'fr/rbac.md' contains a link '#roles-1', but there is no such anchor on this page.
INFO    -  Doc file 'fr/schemas.md' contains a link '#réponse-derreur', but there is no such anchor on this page.
INFO    -  Doc file 'fr/schemas.md' contains a link '#réponse-paginée', but there is no such anchor on this page.
INFO    -  Doc file 'fr/schemas.md' contains a link '#rôle', but there is no such anchor on this page.
INFO    -  Doc file 'fr/schemas.md' contains a link 'security.md#audit-logging', but the doc 'fr/security.md' does not contain an anchor '#audit-logging'.
INFO    -  Doc file 'fr/schemas.md' contains a link 'security.md#session--device-limits', but the doc 'fr/security.md' does not contain an anchor '#session--device-limits'.
INFO    -  Doc file 'fr/security.md' contains a link '#authentification-a-deux-facteurs-2fa--totp', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#shortcut-secure-mode', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#core-settings', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#two-factor-authentication-totp', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#otp-email--sms-verification', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#password-policy', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#rate-limiting--account-lockout', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#session--device-limits', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#security-headers', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#social-login-oauth2', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#webauthn--passkeys-fido2', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#breach-password-check-haveibeenpwned', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#magic-link-passwordless', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#sms-backends', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#email-backends', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#audit-logging', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#organizations-b2b', but there is no such anchor on this page.
INFO    -  Doc file 'fr/settings.md' contains a link '#swappable-models', but there is no such anchor on this page.
INFO    -  Doc file 'fr/troubleshooting.md' contains a link 'periodic_tasks.md#7-encryption-key-rotation-field_encryption_key', but the doc 'fr/periodic_tasks.md' does not contain an anchor '#7-encryption-key-rotation-field_encryption_key'.
INFO    -  Documentation built in 5.55 seconds
