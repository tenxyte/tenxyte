2026-03-20T09:26:08.9085112Z Current runner version: '2.332.0'
2026-03-20T09:26:08.9109642Z ##[group]Runner Image Provisioner
2026-03-20T09:26:08.9110516Z Hosted Compute Agent
2026-03-20T09:26:08.9111125Z Version: 20260213.493
2026-03-20T09:26:08.9111673Z Commit: 5c115507f6dd24b8de37d8bbe0bb4509d0cc0fa3
2026-03-20T09:26:08.9112464Z Build Date: 2026-02-13T00:28:41Z
2026-03-20T09:26:08.9113098Z Worker ID: {1d553664-cba1-4a82-adec-fe00500320b8}
2026-03-20T09:26:08.9113810Z Azure Region: eastus
2026-03-20T09:26:08.9114375Z ##[endgroup]
2026-03-20T09:26:08.9115736Z ##[group]Operating System
2026-03-20T09:26:08.9116727Z Ubuntu
2026-03-20T09:26:08.9117166Z 24.04.3
2026-03-20T09:26:08.9117725Z LTS
2026-03-20T09:26:08.9118149Z ##[endgroup]
2026-03-20T09:26:08.9118629Z ##[group]Runner Image
2026-03-20T09:26:08.9119245Z Image: ubuntu-24.04
2026-03-20T09:26:08.9119753Z Version: 20260309.50.1
2026-03-20T09:26:08.9120971Z Included Software: https://github.com/actions/runner-images/blob/ubuntu24/20260309.50/images/ubuntu/Ubuntu2404-Readme.md
2026-03-20T09:26:08.9122381Z Image Release: https://github.com/actions/runner-images/releases/tag/ubuntu24%2F20260309.50
2026-03-20T09:26:08.9123233Z ##[endgroup]
2026-03-20T09:26:08.9124375Z ##[group]GITHUB_TOKEN Permissions
2026-03-20T09:26:08.9126807Z Contents: read
2026-03-20T09:26:08.9127491Z Metadata: read
2026-03-20T09:26:08.9128316Z Packages: read
2026-03-20T09:26:08.9129118Z ##[endgroup]
2026-03-20T09:26:08.9132164Z Secret source: Actions
2026-03-20T09:26:08.9133147Z Prepare workflow directory
2026-03-20T09:26:08.9457738Z Prepare all required actions
2026-03-20T09:26:08.9494679Z Getting action download info
2026-03-20T09:26:09.3442576Z Download action repository 'actions/checkout@v4' (SHA:34e114876b0b11c390a56381ad16ebd13914f8d5)
2026-03-20T09:26:09.4694830Z Download action repository 'actions/setup-python@v5' (SHA:a26af69be951a213d495a4c3e4e4022e16d87065)
2026-03-20T09:26:09.5550713Z Download action repository 'actions/cache@v4' (SHA:0057852bfaa89a56745cba8c7296529d2fc39830)
2026-03-20T09:26:09.6711833Z Download action repository 'actions/upload-artifact@v4' (SHA:ea165f8d65b6e75b540449e92b4886f43607fa02)
2026-03-20T09:26:09.9536979Z Complete job name: Core Tests (Python 3.12)
2026-03-20T09:26:10.0222382Z ##[group]Run actions/checkout@v4
2026-03-20T09:26:10.0223675Z with:
2026-03-20T09:26:10.0224128Z   repository: tenxyte/tenxyte
2026-03-20T09:26:10.0224833Z   token: ***
2026-03-20T09:26:10.0225251Z   ssh-strict: true
2026-03-20T09:26:10.0225695Z   ssh-user: git
2026-03-20T09:26:10.0226303Z   persist-credentials: true
2026-03-20T09:26:10.0226839Z   clean: true
2026-03-20T09:26:10.0227286Z   sparse-checkout-cone-mode: true
2026-03-20T09:26:10.0227846Z   fetch-depth: 1
2026-03-20T09:26:10.0228294Z   fetch-tags: false
2026-03-20T09:26:10.0228735Z   show-progress: true
2026-03-20T09:26:10.0229181Z   lfs: false
2026-03-20T09:26:10.0229585Z   submodules: false
2026-03-20T09:26:10.0230032Z   set-safe-directory: true
2026-03-20T09:26:10.0230819Z ##[endgroup]
2026-03-20T09:26:10.1313851Z Syncing repository: tenxyte/tenxyte
2026-03-20T09:26:10.1315741Z ##[group]Getting Git version info
2026-03-20T09:26:10.1316879Z Working directory is '/home/runner/work/tenxyte/tenxyte'
2026-03-20T09:26:10.1318030Z [command]/usr/bin/git version
2026-03-20T09:26:10.1387460Z git version 2.53.0
2026-03-20T09:26:10.1414172Z ##[endgroup]
2026-03-20T09:26:10.1430460Z Temporarily overriding HOME='/home/runner/work/_temp/818ccbba-596f-4264-be23-6b330aaf2ae8' before making global git config changes
2026-03-20T09:26:10.1433474Z Adding repository directory to the temporary git global config as a safe directory
2026-03-20T09:26:10.1436454Z [command]/usr/bin/git config --global --add safe.directory /home/runner/work/tenxyte/tenxyte
2026-03-20T09:26:10.1476460Z Deleting the contents of '/home/runner/work/tenxyte/tenxyte'
2026-03-20T09:26:10.1480199Z ##[group]Initializing the repository
2026-03-20T09:26:10.1485124Z [command]/usr/bin/git init /home/runner/work/tenxyte/tenxyte
2026-03-20T09:26:10.1591125Z hint: Using 'master' as the name for the initial branch. This default branch name
2026-03-20T09:26:10.1592832Z hint: will change to "main" in Git 3.0. To configure the initial branch name
2026-03-20T09:26:10.1594494Z hint: to use in all of your new repositories, which will suppress this warning,
2026-03-20T09:26:10.1595542Z hint: call:
2026-03-20T09:26:10.1596458Z hint:
2026-03-20T09:26:10.1597443Z hint: 	git config --global init.defaultBranch <name>
2026-03-20T09:26:10.1598678Z hint:
2026-03-20T09:26:10.1599838Z hint: Names commonly chosen instead of 'master' are 'main', 'trunk' and
2026-03-20T09:26:10.1601852Z hint: 'development'. The just-created branch can be renamed via this command:
2026-03-20T09:26:10.1603382Z hint:
2026-03-20T09:26:10.1604082Z hint: 	git branch -m <name>
2026-03-20T09:26:10.1604926Z hint:
2026-03-20T09:26:10.1606427Z hint: Disable this message with "git config set advice.defaultBranchName false"
2026-03-20T09:26:10.1608628Z Initialized empty Git repository in /home/runner/work/tenxyte/tenxyte/.git/
2026-03-20T09:26:10.1611716Z [command]/usr/bin/git remote add origin https://github.com/tenxyte/tenxyte
2026-03-20T09:26:10.1643966Z ##[endgroup]
2026-03-20T09:26:10.1645325Z ##[group]Disabling automatic garbage collection
2026-03-20T09:26:10.1649174Z [command]/usr/bin/git config --local gc.auto 0
2026-03-20T09:26:10.1679457Z ##[endgroup]
2026-03-20T09:26:10.1680799Z ##[group]Setting up auth
2026-03-20T09:26:10.1687258Z [command]/usr/bin/git config --local --name-only --get-regexp core\.sshCommand
2026-03-20T09:26:10.1719033Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
2026-03-20T09:26:10.2047197Z [command]/usr/bin/git config --local --name-only --get-regexp http\.https\:\/\/github\.com\/\.extraheader
2026-03-20T09:26:10.2075936Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'http\.https\:\/\/github\.com\/\.extraheader' && git config --local --unset-all 'http.https://github.com/.extraheader' || :"
2026-03-20T09:26:10.2305401Z [command]/usr/bin/git config --local --name-only --get-regexp ^includeIf\.gitdir:
2026-03-20T09:26:10.2345124Z [command]/usr/bin/git submodule foreach --recursive git config --local --show-origin --name-only --get-regexp remote.origin.url
2026-03-20T09:26:10.2578776Z [command]/usr/bin/git config --local http.https://github.com/.extraheader AUTHORIZATION: basic ***
2026-03-20T09:26:10.2613628Z ##[endgroup]
2026-03-20T09:26:10.2615154Z ##[group]Fetching the repository
2026-03-20T09:26:10.2624135Z [command]/usr/bin/git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules --depth=1 origin +1e547bd7001e47fecd15ed1715d52684e32e22da:refs/remotes/pull/83/merge
2026-03-20T09:26:10.6920572Z From https://github.com/tenxyte/tenxyte
2026-03-20T09:26:10.6924946Z  * [new ref]         1e547bd7001e47fecd15ed1715d52684e32e22da -> pull/83/merge
2026-03-20T09:26:10.6958059Z ##[endgroup]
2026-03-20T09:26:10.6959990Z ##[group]Determining the checkout info
2026-03-20T09:26:10.6962257Z ##[endgroup]
2026-03-20T09:26:10.6966083Z [command]/usr/bin/git sparse-checkout disable
2026-03-20T09:26:10.7009379Z [command]/usr/bin/git config --local --unset-all extensions.worktreeConfig
2026-03-20T09:26:10.7037608Z ##[group]Checking out the ref
2026-03-20T09:26:10.7040987Z [command]/usr/bin/git checkout --progress --force refs/remotes/pull/83/merge
2026-03-20T09:26:10.7369574Z Note: switching to 'refs/remotes/pull/83/merge'.
2026-03-20T09:26:10.7370902Z 
2026-03-20T09:26:10.7371766Z You are in 'detached HEAD' state. You can look around, make experimental
2026-03-20T09:26:10.7374344Z changes and commit them, and you can discard any commits you make in this
2026-03-20T09:26:10.7378354Z state without impacting any branches by switching back to a branch.
2026-03-20T09:26:10.7380390Z 
2026-03-20T09:26:10.7381679Z If you want to create a new branch to retain commits you create, you may
2026-03-20T09:26:10.7384679Z do so (now or later) by using -c with the switch command. Example:
2026-03-20T09:26:10.7387019Z 
2026-03-20T09:26:10.7387721Z   git switch -c <new-branch-name>
2026-03-20T09:26:10.7388896Z 
2026-03-20T09:26:10.7389572Z Or undo this operation with:
2026-03-20T09:26:10.7390864Z 
2026-03-20T09:26:10.7391449Z   git switch -
2026-03-20T09:26:10.7392046Z 
2026-03-20T09:26:10.7393047Z Turn off this advice by setting config variable advice.detachedHead to false
2026-03-20T09:26:10.7394451Z 
2026-03-20T09:26:10.7396296Z HEAD is now at 1e547bd Merge fd42de96d457c136e8a1a98f5fdf25b653ec1118 into bd8256d4603099605383421e2eba9bec8c9a77a7
2026-03-20T09:26:10.7402146Z ##[endgroup]
2026-03-20T09:26:10.7418848Z [command]/usr/bin/git log -1 --format=%H
2026-03-20T09:26:10.7442647Z 1e547bd7001e47fecd15ed1715d52684e32e22da
2026-03-20T09:26:10.7765283Z ##[group]Run actions/setup-python@v5
2026-03-20T09:26:10.7766551Z with:
2026-03-20T09:26:10.7767330Z   python-version: 3.12
2026-03-20T09:26:10.7768234Z   check-latest: false
2026-03-20T09:26:10.7769345Z   token: ***
2026-03-20T09:26:10.7770191Z   update-environment: true
2026-03-20T09:26:10.7833556Z   allow-prereleases: false
2026-03-20T09:26:10.7834717Z   freethreaded: false
2026-03-20T09:26:10.7835677Z ##[endgroup]
2026-03-20T09:26:10.9543362Z ##[group]Installed versions
2026-03-20T09:26:10.9641736Z Successfully set up CPython (3.12.13)
2026-03-20T09:26:10.9644364Z ##[endgroup]
2026-03-20T09:26:11.0433372Z ##[group]Run actions/cache@v4
2026-03-20T09:26:11.0434317Z with:
2026-03-20T09:26:11.0435023Z   path: ~/.cache/pip
2026-03-20T09:26:11.0437231Z   key: Linux-pip-core-3.12-c8febe590c396cc952abbf25a8326d4687d080c3cce485e94863266c92353169
2026-03-20T09:26:11.0439106Z   restore-keys: Linux-pip-core-3.12-

2026-03-20T09:26:11.0440164Z   enableCrossOsArchive: false
2026-03-20T09:26:11.0441106Z   fail-on-cache-miss: false
2026-03-20T09:26:11.0441987Z   lookup-only: false
2026-03-20T09:26:11.0442767Z   save-always: false
2026-03-20T09:26:11.0443541Z env:
2026-03-20T09:26:11.0444455Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.13/x64
2026-03-20T09:26:11.0446090Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.13/x64/lib/pkgconfig
2026-03-20T09:26:11.0447965Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.13/x64
2026-03-20T09:26:11.0449418Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.13/x64
2026-03-20T09:26:11.0450926Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.13/x64
2026-03-20T09:26:11.0452398Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.13/x64/lib
2026-03-20T09:26:11.0453622Z ##[endgroup]
2026-03-20T09:26:11.2681612Z Cache not found for input keys: Linux-pip-core-3.12-c8febe590c396cc952abbf25a8326d4687d080c3cce485e94863266c92353169, Linux-pip-core-3.12-
2026-03-20T09:26:11.2797468Z ##[group]Run python -m pip install --upgrade pip
2026-03-20T09:26:11.2798840Z [36;1mpython -m pip install --upgrade pip[0m
2026-03-20T09:26:11.2800000Z [36;1mpip install -e ".[core,dev]"[0m
2026-03-20T09:26:11.2857564Z shell: /usr/bin/bash -e {0}
2026-03-20T09:26:11.2858477Z env:
2026-03-20T09:26:11.2859423Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.13/x64
2026-03-20T09:26:11.2861049Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.13/x64/lib/pkgconfig
2026-03-20T09:26:11.2862634Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.13/x64
2026-03-20T09:26:11.2864071Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.13/x64
2026-03-20T09:26:11.2865519Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.13/x64
2026-03-20T09:26:11.2867149Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.13/x64/lib
2026-03-20T09:26:11.2868356Z ##[endgroup]
2026-03-20T09:26:13.5512294Z Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages (26.0.1)
2026-03-20T09:26:14.1203692Z Obtaining file:///home/runner/work/tenxyte/tenxyte
2026-03-20T09:26:14.1226033Z   Installing build dependencies: started
2026-03-20T09:26:14.8270710Z   Installing build dependencies: finished with status 'done'
2026-03-20T09:26:14.8276371Z   Checking if build backend supports build_editable: started
2026-03-20T09:26:14.8761059Z   Checking if build backend supports build_editable: finished with status 'done'
2026-03-20T09:26:14.8770381Z   Getting requirements to build editable: started
2026-03-20T09:26:15.0274253Z   Getting requirements to build editable: finished with status 'done'
2026-03-20T09:26:15.0286689Z   Installing backend dependencies: started
2026-03-20T09:26:15.5392659Z   Installing backend dependencies: finished with status 'done'
2026-03-20T09:26:15.5401105Z   Preparing editable metadata (pyproject.toml): started
2026-03-20T09:26:15.7554146Z   Preparing editable metadata (pyproject.toml): finished with status 'done'
2026-03-20T09:26:15.8741064Z Collecting bcrypt>=4.2 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:15.9269258Z   Downloading bcrypt-5.0.0-cp39-abi3-manylinux_2_34_x86_64.whl.metadata (10 kB)
2026-03-20T09:26:16.1052660Z Collecting cryptography>=42.0 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.1090600Z   Downloading cryptography-46.0.5-cp311-abi3-manylinux_2_34_x86_64.whl.metadata (5.7 kB)
2026-03-20T09:26:16.1282135Z Collecting django-cors-headers>=4.4 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.1317810Z   Downloading django_cors_headers-4.9.0-py3-none-any.whl.metadata (16 kB)
2026-03-20T09:26:16.1801597Z Collecting django>=4.2 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.1833053Z   Downloading django-6.0.3-py3-none-any.whl.metadata (3.9 kB)
2026-03-20T09:26:16.2030708Z Collecting djangorestframework>=3.16 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.2064595Z   Downloading djangorestframework-3.17.0-py3-none-any.whl.metadata (7.9 kB)
2026-03-20T09:26:16.2220604Z Collecting drf-spectacular>=0.27 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.2259503Z   Downloading drf_spectacular-0.29.0-py3-none-any.whl.metadata (14 kB)
2026-03-20T09:26:16.2392694Z Collecting email-validator>=2.0 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.2423829Z   Downloading email_validator-2.3.0-py3-none-any.whl.metadata (26 kB)
2026-03-20T09:26:16.2580937Z Collecting google-auth-oauthlib>=1.2 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.2612989Z   Downloading google_auth_oauthlib-1.3.0-py3-none-any.whl.metadata (2.9 kB)
2026-03-20T09:26:16.2870029Z Collecting google-auth>=2.49.1 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.2904927Z   Downloading google_auth-2.49.1-py3-none-any.whl.metadata (6.2 kB)
2026-03-20T09:26:16.4485617Z Collecting pillow>=11.0 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.4519552Z   Downloading pillow-12.1.1-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl.metadata (8.8 kB)
2026-03-20T09:26:16.5507114Z Collecting pydantic>=2.12 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.5540904Z   Downloading pydantic-2.12.5-py3-none-any.whl.metadata (90 kB)
2026-03-20T09:26:16.5736402Z Collecting pyjwt>=2.12.1 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.5766971Z   Downloading pyjwt-2.12.1-py3-none-any.whl.metadata (4.1 kB)
2026-03-20T09:26:16.5890449Z Collecting pyotp>=2.9 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.5924981Z   Downloading pyotp-2.9.0-py3-none-any.whl.metadata (9.8 kB)
2026-03-20T09:26:16.6049715Z Collecting qrcode>=8.0 (from qrcode[pil]>=8.0->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.6081978Z   Downloading qrcode-8.2-py3-none-any.whl.metadata (17 kB)
2026-03-20T09:26:16.6285795Z Collecting requests>=2.32 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.6316076Z   Downloading requests-2.32.5-py3-none-any.whl.metadata (4.9 kB)
2026-03-20T09:26:16.6532323Z Collecting anyio>=4.0 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.6563042Z   Downloading anyio-4.12.1-py3-none-any.whl.metadata (4.3 kB)
2026-03-20T09:26:16.7035023Z Collecting black>=25.0 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.7069998Z   Downloading black-26.3.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (91 kB)
2026-03-20T09:26:16.8204136Z Collecting mypy>=1.15 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.8242015Z   Downloading mypy-1.19.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (2.2 kB)
2026-03-20T09:26:16.8416626Z Collecting pytest-asyncio>=0.24 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.8451112Z   Downloading pytest_asyncio-1.3.0-py3-none-any.whl.metadata (4.1 kB)
2026-03-20T09:26:16.8591289Z Collecting pytest-cov>=6.0 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.8624923Z   Downloading pytest_cov-7.0.0-py3-none-any.whl.metadata (31 kB)
2026-03-20T09:26:16.8824918Z Collecting pytest-django>=4.9 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.8855821Z   Downloading pytest_django-4.12.0-py3-none-any.whl.metadata (8.0 kB)
2026-03-20T09:26:16.9115952Z Collecting pytest>=8.0 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:16.9146996Z   Downloading pytest-9.0.2-py3-none-any.whl.metadata (7.6 kB)
2026-03-20T09:26:17.2255309Z Collecting ruff>=0.9 (from tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.2290116Z   Downloading ruff-0.15.7-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (26 kB)
2026-03-20T09:26:17.2443211Z Collecting idna>=2.8 (from anyio>=4.0->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.2487944Z   Downloading idna-3.11-py3-none-any.whl.metadata (8.4 kB)
2026-03-20T09:26:17.2648758Z Collecting typing_extensions>=4.5 (from anyio>=4.0->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.2678744Z   Downloading typing_extensions-4.15.0-py3-none-any.whl.metadata (3.3 kB)
2026-03-20T09:26:17.2837759Z Collecting click>=8.0.0 (from black>=25.0->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.2868505Z   Downloading click-8.3.1-py3-none-any.whl.metadata (2.6 kB)
2026-03-20T09:26:17.2966860Z Collecting mypy-extensions>=0.4.3 (from black>=25.0->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.2998460Z   Downloading mypy_extensions-1.1.0-py3-none-any.whl.metadata (1.1 kB)
2026-03-20T09:26:17.3130428Z Collecting packaging>=22.0 (from black>=25.0->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.3142238Z   Using cached packaging-26.0-py3-none-any.whl.metadata (3.3 kB)
2026-03-20T09:26:17.3232831Z Collecting pathspec>=1.0.0 (from black>=25.0->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.3244797Z   Using cached pathspec-1.0.4-py3-none-any.whl.metadata (13 kB)
2026-03-20T09:26:17.3415178Z Collecting platformdirs>=2 (from black>=25.0->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.3446552Z   Downloading platformdirs-4.9.4-py3-none-any.whl.metadata (4.7 kB)
2026-03-20T09:26:17.3590790Z Collecting pytokens~=0.4.0 (from black>=25.0->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.3623130Z   Downloading pytokens-0.4.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (3.8 kB)
2026-03-20T09:26:17.4571032Z Collecting cffi>=2.0.0 (from cryptography>=42.0->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.4605556Z   Downloading cffi-2.0.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl.metadata (2.6 kB)
2026-03-20T09:26:17.4717852Z Collecting pycparser (from cffi>=2.0.0->cryptography>=42.0->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.4749711Z   Downloading pycparser-3.0-py3-none-any.whl.metadata (8.2 kB)
2026-03-20T09:26:17.4912923Z Collecting asgiref>=3.9.1 (from django>=4.2->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.4943736Z   Downloading asgiref-3.11.1-py3-none-any.whl.metadata (9.3 kB)
2026-03-20T09:26:17.5065575Z Collecting sqlparse>=0.5.0 (from django>=4.2->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.5096815Z   Downloading sqlparse-0.5.5-py3-none-any.whl.metadata (4.7 kB)
2026-03-20T09:26:17.5659520Z Collecting uritemplate>=2.0.0 (from drf-spectacular>=0.27->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.5691400Z   Downloading uritemplate-4.2.0-py3-none-any.whl.metadata (2.6 kB)
2026-03-20T09:26:17.6029132Z Collecting PyYAML>=5.1 (from drf-spectacular>=0.27->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.6061204Z   Downloading pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (2.4 kB)
2026-03-20T09:26:17.6279835Z Collecting jsonschema>=2.6.0 (from drf-spectacular>=0.27->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.6311410Z   Downloading jsonschema-4.26.0-py3-none-any.whl.metadata (7.6 kB)
2026-03-20T09:26:17.6426535Z Collecting inflection>=0.3.1 (from drf-spectacular>=0.27->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.6458231Z   Downloading inflection-0.5.1-py2.py3-none-any.whl.metadata (1.7 kB)
2026-03-20T09:26:17.6590283Z Collecting dnspython>=2.0.0 (from email-validator>=2.0->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.6621827Z   Downloading dnspython-2.8.0-py3-none-any.whl.metadata (5.7 kB)
2026-03-20T09:26:17.6839919Z Collecting pyasn1-modules>=0.2.1 (from google-auth>=2.49.1->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.6871077Z   Downloading pyasn1_modules-0.4.2-py3-none-any.whl.metadata (3.5 kB)
2026-03-20T09:26:17.7099607Z Collecting requests-oauthlib>=0.7.0 (from google-auth-oauthlib>=1.2->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.7131290Z   Downloading requests_oauthlib-2.0.0-py2.py3-none-any.whl.metadata (11 kB)
2026-03-20T09:26:17.7281306Z Collecting attrs>=22.2.0 (from jsonschema>=2.6.0->drf-spectacular>=0.27->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.7312871Z   Downloading attrs-26.1.0-py3-none-any.whl.metadata (8.8 kB)
2026-03-20T09:26:17.7440621Z Collecting jsonschema-specifications>=2023.03.6 (from jsonschema>=2.6.0->drf-spectacular>=0.27->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.7474367Z   Downloading jsonschema_specifications-2025.9.1-py3-none-any.whl.metadata (2.9 kB)
2026-03-20T09:26:17.7670910Z Collecting referencing>=0.28.4 (from jsonschema>=2.6.0->drf-spectacular>=0.27->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:17.7701725Z   Downloading referencing-0.37.0-py3-none-any.whl.metadata (2.8 kB)
2026-03-20T09:26:18.0093288Z Collecting rpds-py>=0.25.0 (from jsonschema>=2.6.0->drf-spectacular>=0.27->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:18.0128434Z   Downloading rpds_py-0.30.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (4.1 kB)
2026-03-20T09:26:18.1077796Z Collecting librt>=0.6.2 (from mypy>=1.15->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:18.1111947Z   Downloading librt-0.8.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (1.3 kB)
2026-03-20T09:26:18.1348425Z Collecting pyasn1<0.7.0,>=0.6.1 (from pyasn1-modules>=0.2.1->google-auth>=2.49.1->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:18.1379177Z   Downloading pyasn1-0.6.3-py3-none-any.whl.metadata (8.4 kB)
2026-03-20T09:26:18.1495462Z Collecting annotated-types>=0.6.0 (from pydantic>=2.12->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:18.1526849Z   Downloading annotated_types-0.7.0-py3-none-any.whl.metadata (15 kB)
2026-03-20T09:26:18.7910047Z Collecting pydantic-core==2.41.5 (from pydantic>=2.12->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:18.7944081Z   Downloading pydantic_core-2.41.5-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (7.3 kB)
2026-03-20T09:26:18.8058300Z Collecting typing-inspection>=0.4.2 (from pydantic>=2.12->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:18.8088999Z   Downloading typing_inspection-0.4.2-py3-none-any.whl.metadata (2.6 kB)
2026-03-20T09:26:18.8220490Z Collecting iniconfig>=1.0.1 (from pytest>=8.0->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:18.8251616Z   Downloading iniconfig-2.3.0-py3-none-any.whl.metadata (2.5 kB)
2026-03-20T09:26:18.8360148Z Collecting pluggy<2,>=1.5 (from pytest>=8.0->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:18.8372039Z   Using cached pluggy-1.6.0-py3-none-any.whl.metadata (4.8 kB)
2026-03-20T09:26:18.8535385Z Collecting pygments>=2.7.2 (from pytest>=8.0->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:18.8567574Z   Downloading pygments-2.19.2-py3-none-any.whl.metadata (2.5 kB)
2026-03-20T09:26:19.2671422Z Collecting coverage>=7.10.6 (from coverage[toml]>=7.10.6->pytest-cov>=6.0->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:19.2712434Z   Downloading coverage-7.13.5-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl.metadata (8.5 kB)
2026-03-20T09:26:19.3659021Z Collecting charset_normalizer<4,>=2 (from requests>=2.32->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:19.3692767Z   Downloading charset_normalizer-3.4.6-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (40 kB)
2026-03-20T09:26:19.3940878Z Collecting urllib3<3,>=1.21.1 (from requests>=2.32->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:19.3973175Z   Downloading urllib3-2.6.3-py3-none-any.whl.metadata (6.9 kB)
2026-03-20T09:26:19.4168774Z Collecting certifi>=2017.4.17 (from requests>=2.32->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:19.4199674Z   Downloading certifi-2026.2.25-py3-none-any.whl.metadata (2.5 kB)
2026-03-20T09:26:19.4345239Z Collecting oauthlib>=3.0.0 (from requests-oauthlib>=0.7.0->google-auth-oauthlib>=1.2->tenxyte==0.9.3.1.5.2)
2026-03-20T09:26:19.4376898Z   Downloading oauthlib-3.3.1-py3-none-any.whl.metadata (7.9 kB)
2026-03-20T09:26:19.4524425Z Downloading anyio-4.12.1-py3-none-any.whl (113 kB)
2026-03-20T09:26:19.4584820Z Downloading bcrypt-5.0.0-cp39-abi3-manylinux_2_34_x86_64.whl (278 kB)
2026-03-20T09:26:19.4647705Z Downloading black-26.3.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (1.8 MB)
2026-03-20T09:26:19.4875528Z    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.8/1.8 MB 78.9 MB/s  0:00:00
2026-03-20T09:26:19.4908892Z Downloading pytokens-0.4.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (269 kB)
2026-03-20T09:26:19.4970424Z Downloading click-8.3.1-py3-none-any.whl (108 kB)
2026-03-20T09:26:19.5028946Z Downloading cryptography-46.0.5-cp311-abi3-manylinux_2_34_x86_64.whl (4.5 MB)
2026-03-20T09:26:19.5242971Z    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.5/4.5 MB 225.7 MB/s  0:00:00
2026-03-20T09:26:19.5276545Z Downloading cffi-2.0.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (219 kB)
2026-03-20T09:26:19.5338876Z Downloading django-6.0.3-py3-none-any.whl (8.4 MB)
2026-03-20T09:26:19.5704005Z    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.4/8.4 MB 240.0 MB/s  0:00:00
2026-03-20T09:26:19.5735502Z Downloading asgiref-3.11.1-py3-none-any.whl (24 kB)
2026-03-20T09:26:19.5787816Z Downloading django_cors_headers-4.9.0-py3-none-any.whl (12 kB)
2026-03-20T09:26:19.5848096Z Downloading djangorestframework-3.17.0-py3-none-any.whl (898 kB)
2026-03-20T09:26:19.5938510Z    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 898.8/898.8 kB 109.7 MB/s  0:00:00
2026-03-20T09:26:19.5982394Z Downloading drf_spectacular-0.29.0-py3-none-any.whl (105 kB)
2026-03-20T09:26:19.6043361Z Downloading email_validator-2.3.0-py3-none-any.whl (35 kB)
2026-03-20T09:26:19.6097958Z Downloading dnspython-2.8.0-py3-none-any.whl (331 kB)
2026-03-20T09:26:19.6163845Z Downloading google_auth-2.49.1-py3-none-any.whl (240 kB)
2026-03-20T09:26:19.6222404Z Downloading google_auth_oauthlib-1.3.0-py3-none-any.whl (19 kB)
2026-03-20T09:26:19.6274049Z Downloading idna-3.11-py3-none-any.whl (71 kB)
2026-03-20T09:26:19.6330561Z Downloading inflection-0.5.1-py2.py3-none-any.whl (9.5 kB)
2026-03-20T09:26:19.6388371Z Downloading jsonschema-4.26.0-py3-none-any.whl (90 kB)
2026-03-20T09:26:19.6445955Z Downloading attrs-26.1.0-py3-none-any.whl (67 kB)
2026-03-20T09:26:19.6499562Z Downloading jsonschema_specifications-2025.9.1-py3-none-any.whl (18 kB)
2026-03-20T09:26:19.6551884Z Downloading mypy-1.19.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (13.6 MB)
2026-03-20T09:26:19.7129920Z    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 13.6/13.6 MB 244.4 MB/s  0:00:00
2026-03-20T09:26:19.7161063Z Downloading librt-0.8.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (224 kB)
2026-03-20T09:26:19.7224409Z Downloading mypy_extensions-1.1.0-py3-none-any.whl (5.0 kB)
2026-03-20T09:26:19.7254743Z Using cached packaging-26.0-py3-none-any.whl (74 kB)
2026-03-20T09:26:19.7266377Z Using cached pathspec-1.0.4-py3-none-any.whl (55 kB)
2026-03-20T09:26:19.7300159Z Downloading pillow-12.1.1-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl (7.0 MB)
2026-03-20T09:26:19.7618586Z    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 7.0/7.0 MB 233.4 MB/s  0:00:00
2026-03-20T09:26:19.7648676Z Downloading platformdirs-4.9.4-py3-none-any.whl (21 kB)
2026-03-20T09:26:19.7704223Z Downloading pyasn1_modules-0.4.2-py3-none-any.whl (181 kB)
2026-03-20T09:26:19.7762386Z Downloading pyasn1-0.6.3-py3-none-any.whl (83 kB)
2026-03-20T09:26:19.7819792Z Downloading pydantic-2.12.5-py3-none-any.whl (463 kB)
2026-03-20T09:26:19.7886769Z Downloading pydantic_core-2.41.5-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (2.1 MB)
2026-03-20T09:26:19.8005508Z    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.1/2.1 MB 198.2 MB/s  0:00:00
2026-03-20T09:26:19.8039104Z Downloading annotated_types-0.7.0-py3-none-any.whl (13 kB)
2026-03-20T09:26:19.8093347Z Downloading pyjwt-2.12.1-py3-none-any.whl (29 kB)
2026-03-20T09:26:19.8143896Z Downloading pyotp-2.9.0-py3-none-any.whl (13 kB)
2026-03-20T09:26:19.8195651Z Downloading pytest-9.0.2-py3-none-any.whl (374 kB)
2026-03-20T09:26:19.8239309Z Using cached pluggy-1.6.0-py3-none-any.whl (20 kB)
2026-03-20T09:26:19.8269797Z Downloading iniconfig-2.3.0-py3-none-any.whl (7.5 kB)
2026-03-20T09:26:19.8321936Z Downloading pygments-2.19.2-py3-none-any.whl (1.2 MB)
2026-03-20T09:26:19.8404954Z    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2/1.2 MB 165.3 MB/s  0:00:00
2026-03-20T09:26:19.8434658Z Downloading pytest_asyncio-1.3.0-py3-none-any.whl (15 kB)
2026-03-20T09:26:19.8484042Z Downloading pytest_cov-7.0.0-py3-none-any.whl (22 kB)
2026-03-20T09:26:19.8540442Z Downloading coverage-7.13.5-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (254 kB)
2026-03-20T09:26:19.8599586Z Downloading pytest_django-4.12.0-py3-none-any.whl (26 kB)
2026-03-20T09:26:19.8654816Z Downloading pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (807 kB)
2026-03-20T09:26:19.8717326Z    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 807.9/807.9 kB 134.3 MB/s  0:00:00
2026-03-20T09:26:19.8748015Z Downloading qrcode-8.2-py3-none-any.whl (45 kB)
2026-03-20T09:26:19.8797005Z Downloading referencing-0.37.0-py3-none-any.whl (26 kB)
2026-03-20T09:26:19.8849333Z Downloading requests-2.32.5-py3-none-any.whl (64 kB)
2026-03-20T09:26:19.8905232Z Downloading charset_normalizer-3.4.6-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (207 kB)
2026-03-20T09:26:19.8965042Z Downloading urllib3-2.6.3-py3-none-any.whl (131 kB)
2026-03-20T09:26:19.9024265Z Downloading certifi-2026.2.25-py3-none-any.whl (153 kB)
2026-03-20T09:26:19.9080667Z Downloading requests_oauthlib-2.0.0-py2.py3-none-any.whl (24 kB)
2026-03-20T09:26:19.9131250Z Downloading oauthlib-3.3.1-py3-none-any.whl (160 kB)
2026-03-20T09:26:19.9187086Z Downloading rpds_py-0.30.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (394 kB)
2026-03-20T09:26:19.9254793Z Downloading ruff-0.15.7-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (11.2 MB)
2026-03-20T09:26:19.9719051Z    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 11.2/11.2 MB 253.0 MB/s  0:00:00
2026-03-20T09:26:19.9753619Z Downloading sqlparse-0.5.5-py3-none-any.whl (46 kB)
2026-03-20T09:26:19.9807627Z Downloading typing_extensions-4.15.0-py3-none-any.whl (44 kB)
2026-03-20T09:26:19.9865770Z Downloading typing_inspection-0.4.2-py3-none-any.whl (14 kB)
2026-03-20T09:26:19.9916347Z Downloading uritemplate-4.2.0-py3-none-any.whl (11 kB)
2026-03-20T09:26:19.9972168Z Downloading pycparser-3.0-py3-none-any.whl (48 kB)
2026-03-20T09:26:20.1099387Z Building wheels for collected packages: tenxyte
2026-03-20T09:26:20.1107820Z   Building editable for tenxyte (pyproject.toml): started
2026-03-20T09:26:20.1470842Z   Building editable for tenxyte (pyproject.toml): finished with status 'done'
2026-03-20T09:26:20.1475893Z   Created wheel for tenxyte: filename=tenxyte-0.9.3.1.5.2-py3-none-any.whl size=10848 sha256=19f9af127b83608cc7c2c5b1f917c13e44514ec42b9328c3afbc550291a695ef
2026-03-20T09:26:20.1478239Z   Stored in directory: /tmp/pip-ephem-wheel-cache-eqepbhja/wheels/f7/b1/93/9a210d1cc3591de94b54affb710e93ea5011d7234914cb9aa4
2026-03-20T09:26:20.1512492Z Successfully built tenxyte
2026-03-20T09:26:20.2832910Z Installing collected packages: urllib3, uritemplate, typing_extensions, sqlparse, ruff, rpds-py, qrcode, PyYAML, pytokens, pyotp, pyjwt, pygments, pycparser, pyasn1, pluggy, platformdirs, pillow, pathspec, packaging, oauthlib, mypy-extensions, librt, iniconfig, inflection, idna, dnspython, coverage, click, charset_normalizer, certifi, bcrypt, attrs, asgiref, annotated-types, typing-inspection, requests, referencing, pytest, pydantic-core, pyasn1-modules, mypy, email-validator, django, cffi, black, anyio, requests-oauthlib, pytest-django, pytest-cov, pytest-asyncio, pydantic, jsonschema-specifications, djangorestframework, django-cors-headers, cryptography, jsonschema, google-auth, google-auth-oauthlib, drf-spectacular, tenxyte
2026-03-20T09:26:27.8212711Z 
2026-03-20T09:26:27.8268371Z Successfully installed PyYAML-6.0.3 annotated-types-0.7.0 anyio-4.12.1 asgiref-3.11.1 attrs-26.1.0 bcrypt-5.0.0 black-26.3.1 certifi-2026.2.25 cffi-2.0.0 charset_normalizer-3.4.6 click-8.3.1 coverage-7.13.5 cryptography-46.0.5 django-6.0.3 django-cors-headers-4.9.0 djangorestframework-3.17.0 dnspython-2.8.0 drf-spectacular-0.29.0 email-validator-2.3.0 google-auth-2.49.1 google-auth-oauthlib-1.3.0 idna-3.11 inflection-0.5.1 iniconfig-2.3.0 jsonschema-4.26.0 jsonschema-specifications-2025.9.1 librt-0.8.1 mypy-1.19.1 mypy-extensions-1.1.0 oauthlib-3.3.1 packaging-26.0 pathspec-1.0.4 pillow-12.1.1 platformdirs-4.9.4 pluggy-1.6.0 pyasn1-0.6.3 pyasn1-modules-0.4.2 pycparser-3.0 pydantic-2.12.5 pydantic-core-2.41.5 pygments-2.19.2 pyjwt-2.12.1 pyotp-2.9.0 pytest-9.0.2 pytest-asyncio-1.3.0 pytest-cov-7.0.0 pytest-django-4.12.0 pytokens-0.4.1 qrcode-8.2 referencing-0.37.0 requests-2.32.5 requests-oauthlib-2.0.0 rpds-py-0.30.0 ruff-0.15.7 sqlparse-0.5.5 tenxyte-0.9.3.1.5.2 typing-inspection-0.4.2 typing_extensions-4.15.0 uritemplate-4.2.0 urllib3-2.6.3
2026-03-20T09:26:28.3244490Z ##[group]Run pytest tests/core/ -p no:django --no-cov -q
2026-03-20T09:26:28.3244927Z [36;1mpytest tests/core/ -p no:django --no-cov -q[0m
2026-03-20T09:26:28.3295525Z shell: /usr/bin/bash -e {0}
2026-03-20T09:26:28.3295769Z env:
2026-03-20T09:26:28.3296034Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.13/x64
2026-03-20T09:26:28.3296756Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.13/x64/lib/pkgconfig
2026-03-20T09:26:28.3297191Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.13/x64
2026-03-20T09:26:28.3297579Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.13/x64
2026-03-20T09:26:28.3297959Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.13/x64
2026-03-20T09:26:28.3298336Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.13/x64/lib
2026-03-20T09:26:28.3298653Z ##[endgroup]
2026-03-20T09:26:30.2166513Z ........................................................................ [ 20%]
2026-03-20T09:27:30.0641674Z ........................................................................ [ 40%]
2026-03-20T09:27:30.1223961Z ........................................................................ [ 60%]
2026-03-20T09:27:30.2249297Z ........................................................................ [ 81%]
2026-03-20T09:27:53.6747415Z ........................................sss........................      [100%]
2026-03-20T09:27:53.6748197Z =============================== warnings summary ===============================
2026-03-20T09:27:53.6749311Z ../../../../../opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/_pytest/config/__init__.py:1428
2026-03-20T09:27:53.6751141Z   /opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/_pytest/config/__init__.py:1428: PytestConfigWarning: Unknown config option: DJANGO_SETTINGS_MODULE
2026-03-20T09:27:53.6752529Z   
2026-03-20T09:27:53.6752917Z     self._warn_or_fail_if_strict(f"Unknown config option: {key}\n")
2026-03-20T09:27:53.6753177Z 
2026-03-20T09:27:53.6753426Z tests/core/test_jwt_service.py::test_create_access_token
2026-03-20T09:27:53.6753767Z tests/core/test_jwt_service.py::test_validate_token
2026-03-20T09:27:53.6754100Z tests/core/test_jwt_service.py::test_blacklist_token
2026-03-20T09:27:53.6755052Z   /opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/jwt/api_jwt.py:147: InsecureKeyLengthWarning: The HMAC key is 16 bytes long, which is below the minimum recommended length of 32 bytes for SHA256. See RFC 7518 Section 3.2.
2026-03-20T09:27:53.6756498Z     return self._jws.encode(
2026-03-20T09:27:53.6756652Z 
2026-03-20T09:27:53.6756777Z tests/core/test_jwt_service.py::test_validate_token
2026-03-20T09:27:53.6757106Z tests/core/test_jwt_service.py::test_blacklist_token
2026-03-20T09:27:53.6758033Z   /opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/jwt/api_jwt.py:365: InsecureKeyLengthWarning: The HMAC key is 16 bytes long, which is below the minimum recommended length of 32 bytes for SHA256. See RFC 7518 Section 3.2.
2026-03-20T09:27:53.6759298Z     decoded = self.decode_complete(
2026-03-20T09:27:53.6759467Z 
2026-03-20T09:27:53.6759675Z -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2026-03-20T09:27:53.6760122Z 352 passed, 3 skipped, 6 warnings in 84.29s (0:01:24)
2026-03-20T09:27:53.7492418Z ##[group]Run pytest tests/core/ -p no:django --cov=tenxyte.core --cov-report=xml:coverage-core.xml --cov-report=term -q
2026-03-20T09:27:53.7493261Z [36;1mpytest tests/core/ -p no:django --cov=tenxyte.core --cov-report=xml:coverage-core.xml --cov-report=term -q[0m
2026-03-20T09:27:53.7542926Z shell: /usr/bin/bash -e {0}
2026-03-20T09:27:53.7543149Z env:
2026-03-20T09:27:53.7543398Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.13/x64
2026-03-20T09:27:53.7543822Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.13/x64/lib/pkgconfig
2026-03-20T09:27:53.7544242Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.13/x64
2026-03-20T09:27:53.7544599Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.13/x64
2026-03-20T09:27:53.7544957Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.13/x64
2026-03-20T09:27:53.7545318Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.13/x64/lib
2026-03-20T09:27:53.7545611Z ##[endgroup]
2026-03-20T09:27:55.3791231Z ........................................................................ [ 20%]
2026-03-20T09:28:55.7590477Z ........................................................................ [ 40%]
2026-03-20T09:28:55.8574753Z ........................................................................ [ 60%]
2026-03-20T09:28:56.0432012Z ........................................................................ [ 81%]
2026-03-20T09:29:24.6100051Z ........................................sss........................
2026-03-20T09:29:24.6102296Z ERROR: Coverage failure: total of 23 is less than fail-under=90
2026-03-20T09:29:24.6112367Z                                                                          [100%]
2026-03-20T09:29:24.6113425Z =============================== warnings summary ===============================
2026-03-20T09:29:24.6114638Z ../../../../../opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/_pytest/config/__init__.py:1428
2026-03-20T09:29:24.6117005Z   /opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/_pytest/config/__init__.py:1428: PytestConfigWarning: Unknown config option: DJANGO_SETTINGS_MODULE
2026-03-20T09:29:24.6118481Z   
2026-03-20T09:29:24.6119007Z     self._warn_or_fail_if_strict(f"Unknown config option: {key}\n")
2026-03-20T09:29:24.6119451Z 
2026-03-20T09:29:24.6119738Z tests/core/test_jwt_service.py::test_create_access_token
2026-03-20T09:29:24.6120260Z tests/core/test_jwt_service.py::test_validate_token
2026-03-20T09:29:24.6120609Z tests/core/test_jwt_service.py::test_blacklist_token
2026-03-20T09:29:24.6121566Z   /opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/jwt/api_jwt.py:147: InsecureKeyLengthWarning: The HMAC key is 16 bytes long, which is below the minimum recommended length of 32 bytes for SHA256. See RFC 7518 Section 3.2.
2026-03-20T09:29:24.6122512Z     return self._jws.encode(
2026-03-20T09:29:24.6122656Z 
2026-03-20T09:29:24.6122780Z tests/core/test_jwt_service.py::test_validate_token
2026-03-20T09:29:24.6123125Z tests/core/test_jwt_service.py::test_blacklist_token
2026-03-20T09:29:24.6124076Z   /opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/jwt/api_jwt.py:365: InsecureKeyLengthWarning: The HMAC key is 16 bytes long, which is below the minimum recommended length of 32 bytes for SHA256. See RFC 7518 Section 3.2.
2026-03-20T09:29:24.6125236Z     decoded = self.decode_complete(
2026-03-20T09:29:24.6125399Z 
2026-03-20T09:29:24.6125600Z -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2026-03-20T09:29:24.6126008Z ================================ tests coverage ================================
2026-03-20T09:29:24.6126671Z _______________ coverage: platform linux, python 3.12.13-final-0 _______________
2026-03-20T09:29:24.6126950Z 
2026-03-20T09:29:24.6127093Z Name                                                          Stmts   Miss  Cover   Missing
2026-03-20T09:29:24.6127503Z -------------------------------------------------------------------------------------------
2026-03-20T09:29:24.6128150Z src/tenxyte/__init__.py                                          50     42    16%   74-76, 101-161
2026-03-20T09:29:24.6128636Z src/tenxyte/adapters/django/__init__.py                           6      0   100%
2026-03-20T09:29:24.6129419Z src/tenxyte/adapters/django/cache_service.py                     87     64    26%   49-50, 54-58, 70, 84-85, 97-98, 114, 127-133, 149-154, 170-187, 191-192, 212-213, 227-229, 235-239, 243, 249-254, 258-272, 292
2026-03-20T09:29:24.6130432Z src/tenxyte/adapters/django/email_service.py                    112     94    16%   51, 55-59, 88-120, 137-148, 160-173, 192-196, 224-246, 250-271, 275-304, 308-323, 327-350, 354-371, 391-392
2026-03-20T09:29:24.6131338Z src/tenxyte/adapters/django/middleware.py                       110     77    30%   39-69, 83-99, 111-121, 139-141, 146-149, 154-190, 206, 219, 224-242, 253, 264, 275, 286
2026-03-20T09:29:24.6132082Z src/tenxyte/adapters/django/settings_provider.py                 26     16    38%   10, 35, 39-43, 56-61, 66, 86-92
2026-03-20T09:29:24.6132696Z src/tenxyte/adapters/django/task_service.py                      37     11    70%   23-26, 39-40, 49-54
2026-03-20T09:29:24.6133202Z src/tenxyte/admin.py                                            303    303     0%   1-601
2026-03-20T09:29:24.6133622Z src/tenxyte/apps.py                                              47     47     0%   1-123
2026-03-20T09:29:24.6134068Z src/tenxyte/authentication.py                                    40     40     0%   5-76
2026-03-20T09:29:24.6134532Z src/tenxyte/backends/__init__.py                                  0      0   100%
2026-03-20T09:29:24.6134993Z src/tenxyte/backends/email.py                                    81     81     0%   24-251
2026-03-20T09:29:24.6135452Z src/tenxyte/backends/sms.py                                      72     72     0%   5-167
2026-03-20T09:29:24.6135889Z src/tenxyte/conf/__init__.py                                     12     12     0%   5-32
2026-03-20T09:29:24.6136532Z src/tenxyte/conf/airs.py                                         34     34     0%   1-64
2026-03-20T09:29:24.6136957Z src/tenxyte/conf/auth.py                                         67     67     0%   1-119
2026-03-20T09:29:24.6137380Z src/tenxyte/conf/base.py                                         49     49     0%   1-135
2026-03-20T09:29:24.6137831Z src/tenxyte/conf/communication.py                                38     38     0%   1-98
2026-03-20T09:29:24.6138281Z src/tenxyte/conf/jwt.py                                          40     40     0%   1-85
2026-03-20T09:29:24.6138719Z src/tenxyte/conf/modules.py                                      19     19     0%   1-48
2026-03-20T09:29:24.6139157Z src/tenxyte/conf/presets.py                                       2      2     0%   1-80
2026-03-20T09:29:24.6139602Z src/tenxyte/conf/security.py                                     76     76     0%   1-208
2026-03-20T09:29:24.6140042Z src/tenxyte/conf/social.py                                       53     53     0%   1-108
2026-03-20T09:29:24.6140483Z src/tenxyte/core/__init__.py                                     12      0   100%
2026-03-20T09:29:24.6140923Z src/tenxyte/core/cache_service.py                               140      0   100%
2026-03-20T09:29:24.6141368Z src/tenxyte/core/email_service.py                                91      0   100%
2026-03-20T09:29:24.6141969Z src/tenxyte/core/env_provider.py                                 53      1    98%   13
2026-03-20T09:29:24.6142470Z src/tenxyte/core/jwt_service.py                                 277     15    95%   507, 513, 603, 620, 854-875, 891
2026-03-20T09:29:24.6143007Z src/tenxyte/core/magic_link_service.py                          200      4    98%   308-310, 362
2026-03-20T09:29:24.6143495Z src/tenxyte/core/middleware.py                                  155      0   100%
2026-03-20T09:29:24.6143947Z src/tenxyte/core/schemas.py                                     210      6    97%   132-137
2026-03-20T09:29:24.6144590Z src/tenxyte/core/session_service.py                             134      4    97%   196, 242, 265, 297
2026-03-20T09:29:24.6145091Z src/tenxyte/core/settings.py                                    151      2    99%   149, 253
2026-03-20T09:29:24.6145550Z src/tenxyte/core/task_service.py                                 12      0   100%
2026-03-20T09:29:24.6146048Z src/tenxyte/core/totp_service.py                                358      8    98%   187-192, 202-207, 699, 761
2026-03-20T09:29:24.6146769Z src/tenxyte/core/webauthn_service.py                            162      1    99%   27
2026-03-20T09:29:24.6147242Z src/tenxyte/decorators.py                                       315    315     0%   1-748
2026-03-20T09:29:24.6147686Z src/tenxyte/device_info.py                                      200    200     0%   21-424
2026-03-20T09:29:24.6148123Z src/tenxyte/docs/__init__.py                                      0      0   100%
2026-03-20T09:29:24.6148554Z src/tenxyte/docs/schemas.py                                      56     56     0%   7-488
2026-03-20T09:29:24.6148999Z src/tenxyte/exceptions.py                                        51     51     0%   15-86
2026-03-20T09:29:24.6149435Z src/tenxyte/filters.py                                          121    121     0%   15-371
2026-03-20T09:29:24.6149880Z src/tenxyte/management/__init__.py                                0      0   100%
2026-03-20T09:29:24.6150429Z src/tenxyte/management/commands/__init__.py                       0      0   100%
2026-03-20T09:29:24.6150976Z src/tenxyte/management/commands/tenxyte_cleanup.py               79     79     0%   1-115
2026-03-20T09:29:24.6151531Z src/tenxyte/management/commands/tenxyte_purge_audit_logs.py      27     27     0%   13-77
2026-03-20T09:29:24.6152102Z src/tenxyte/management/commands/tenxyte_quickstart.py            68     68     0%   10-115
2026-03-20T09:29:24.6152611Z src/tenxyte/middleware.py                                       204    204     0%   1-433
2026-03-20T09:29:24.6153056Z src/tenxyte/models/__init__.py                                   13     13     0%   9-94
2026-03-20T09:29:24.6153512Z src/tenxyte/models/agent.py                                      69     69     0%   1-129
2026-03-20T09:29:24.6153977Z src/tenxyte/models/application.py                                52     52     0%   9-106
2026-03-20T09:29:24.6154449Z src/tenxyte/models/auth.py                                      305    305     0%   12-721
2026-03-20T09:29:24.6154888Z src/tenxyte/models/base.py                                       57     57     0%   9-122
2026-03-20T09:29:24.6155324Z src/tenxyte/models/gdpr.py                                       82     82     0%   8-185
2026-03-20T09:29:24.6155776Z src/tenxyte/models/magic_link.py                                 58     58     0%   8-128
2026-03-20T09:29:24.6156538Z src/tenxyte/models/operational.py                                99     99     0%   10-237
2026-03-20T09:29:24.6157052Z src/tenxyte/models/organization.py                              179    179     0%   14-495
2026-03-20T09:29:24.6157536Z src/tenxyte/models/security.py                                  103    103     0%   10-346
2026-03-20T09:29:24.6158006Z src/tenxyte/models/social.py                                     26     26     0%   8-97
2026-03-20T09:29:24.6158458Z src/tenxyte/models/tenant.py                                     29     29     0%   8-106
2026-03-20T09:29:24.6159218Z src/tenxyte/models/webauthn.py                                   47     47     0%   9-103
2026-03-20T09:29:24.6159675Z src/tenxyte/pagination.py                                        16     16     0%   10-109
2026-03-20T09:29:24.6160119Z src/tenxyte/ports/__init__.py                                     2      2     0%   3-21
2026-03-20T09:29:24.6160586Z src/tenxyte/ports/repositories.py                               177    177     0%   8-378
2026-03-20T09:29:24.6161069Z src/tenxyte/serializers/__init__.py                              10     10     0%   9-94
2026-03-20T09:29:24.6161571Z src/tenxyte/serializers/application_serializers.py               16     16     0%   5-34
2026-03-20T09:29:24.6162219Z src/tenxyte/serializers/auth_serializers.py                      81     81     0%   5-183
2026-03-20T09:29:24.6162746Z src/tenxyte/serializers/gdpr_admin_serializers.py                14     14     0%   5-43
2026-03-20T09:29:24.6163315Z src/tenxyte/serializers/organization_serializers.py              82     82     0%   5-172
2026-03-20T09:29:24.6163864Z src/tenxyte/serializers/otp_serializers.py                        5      5     0%   5-13
2026-03-20T09:29:24.6164392Z src/tenxyte/serializers/password_serializers.py                  13     13     0%   5-38
2026-03-20T09:29:24.6164925Z src/tenxyte/serializers/rbac_serializers.py                      79     79     0%   5-122
2026-03-20T09:29:24.6165456Z src/tenxyte/serializers/security_serializers.py                  56     56     0%   7-135
2026-03-20T09:29:24.6165988Z src/tenxyte/serializers/twofa_serializers.py                     16     16     0%   5-37
2026-03-20T09:29:24.6166769Z src/tenxyte/serializers/user_admin_serializers.py                39     39     0%   5-117
2026-03-20T09:29:24.6167266Z src/tenxyte/services/__init__.py                                  4      4     0%   1-5
2026-03-20T09:29:24.6167771Z src/tenxyte/services/account_deletion_service.py                 95     95     0%   5-461
2026-03-20T09:29:24.6168289Z src/tenxyte/services/agent_service.py                           180    180     0%   1-360
2026-03-20T09:29:24.6168803Z src/tenxyte/services/breach_check_service.py                      9      9     0%   14-113
2026-03-20T09:29:24.6169320Z src/tenxyte/services/email_service.py                             2      2     0%   8-10
2026-03-20T09:29:24.6169847Z src/tenxyte/services/organization_service.py                    176    176     0%   12-606
2026-03-20T09:29:24.6170365Z src/tenxyte/services/otp_service.py                              73     73     0%   1-190
2026-03-20T09:29:24.6170868Z src/tenxyte/services/social_auth_service.py                     187    187     0%   13-502
2026-03-20T09:29:24.6171382Z src/tenxyte/services/stats_service.py                            95     95     0%   7-339
2026-03-20T09:29:24.6171846Z src/tenxyte/signals.py                                           44     44     0%   28-143
2026-03-20T09:29:24.6172284Z src/tenxyte/tasks/__init__.py                                     0      0   100%
2026-03-20T09:29:24.6172743Z src/tenxyte/tasks/agent_tasks.py                                 24     24     0%   1-46
2026-03-20T09:29:24.6173201Z src/tenxyte/tenant_context.py                                     7      7     0%   7-36
2026-03-20T09:29:24.6173653Z src/tenxyte/throttles.py                                        130    130     0%   11-344
2026-03-20T09:29:24.6174074Z src/tenxyte/urls.py                                              14     14     0%   1-253
2026-03-20T09:29:24.6174502Z src/tenxyte/validators.py                                        34     34     0%   11-301
2026-03-20T09:29:24.6174948Z src/tenxyte/views/__init__.py                                     9      9     0%   1-58
2026-03-20T09:29:24.6175428Z src/tenxyte/views/account_deletion_views.py                      51     51     0%   5-493
2026-03-20T09:29:24.6175918Z src/tenxyte/views/agent_views.py                                132    132     0%   1-614
2026-03-20T09:29:24.6176696Z src/tenxyte/views/application_views.py                           90     90     0%   1-382
2026-03-20T09:29:24.6177178Z src/tenxyte/views/auth_views.py                                 156    156     0%   8-1242
2026-03-20T09:29:24.6177657Z src/tenxyte/views/dashboard_views.py                             36     36     0%   7-194
2026-03-20T09:29:24.6178146Z src/tenxyte/views/gdpr_admin_views.py                            82     82     0%   11-377
2026-03-20T09:29:24.6178626Z src/tenxyte/views/magic_link_views.py                            83     83     0%   8-345
2026-03-20T09:29:24.6179128Z src/tenxyte/views/organization_views.py                         140    140     0%   8-1065
2026-03-20T09:29:24.6179735Z src/tenxyte/views/otp_views.py                                   36     36     0%   1-224
2026-03-20T09:29:24.6180214Z src/tenxyte/views/password_views.py                              49     49     0%   8-507
2026-03-20T09:29:24.6180686Z src/tenxyte/views/rbac_views.py                                 263    263     0%   1-929
2026-03-20T09:29:24.6181161Z src/tenxyte/views/security_views.py                             138    138     0%   8-597
2026-03-20T09:29:24.6181649Z src/tenxyte/views/social_auth_views.py                           78     78     0%   8-388
2026-03-20T09:29:24.6182126Z src/tenxyte/views/twofa_views.py                                 93     93     0%   8-446
2026-03-20T09:29:24.6182626Z src/tenxyte/views/user_views.py                                 203    203     0%   8-885
2026-03-20T09:29:24.6183099Z src/tenxyte/views/webauthn_views.py                              55     55     0%   16-500
2026-03-20T09:29:24.6183559Z -------------------------------------------------------------------------------------------
2026-03-20T09:29:24.6183966Z TOTAL                                                          8930   6892    23%
2026-03-20T09:29:24.6184279Z Coverage HTML written to dir htmlcov
2026-03-20T09:29:24.6184562Z Coverage XML written to file coverage-core.xml
2026-03-20T09:29:24.7356932Z FAIL Required test coverage of 90% not reached. Total coverage: 22.82%
2026-03-20T09:29:24.7357873Z 352 passed, 3 skipped, 6 warnings in 90.36s (0:01:30)
2026-03-20T09:29:24.8219565Z ##[error]Process completed with exit code 1.
2026-03-20T09:29:24.8333999Z Post job cleanup.
2026-03-20T09:29:24.9290781Z [command]/usr/bin/git version
2026-03-20T09:29:24.9333645Z git version 2.53.0
2026-03-20T09:29:24.9377743Z Temporarily overriding HOME='/home/runner/work/_temp/2dc43a0d-fd69-4ea2-80fb-82c322086be1' before making global git config changes
2026-03-20T09:29:24.9379107Z Adding repository directory to the temporary git global config as a safe directory
2026-03-20T09:29:24.9384028Z [command]/usr/bin/git config --global --add safe.directory /home/runner/work/tenxyte/tenxyte
2026-03-20T09:29:24.9420466Z [command]/usr/bin/git config --local --name-only --get-regexp core\.sshCommand
2026-03-20T09:29:24.9455104Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
2026-03-20T09:29:24.9699917Z [command]/usr/bin/git config --local --name-only --get-regexp http\.https\:\/\/github\.com\/\.extraheader
2026-03-20T09:29:24.9720946Z http.https://github.com/.extraheader
2026-03-20T09:29:24.9733082Z [command]/usr/bin/git config --local --unset-all http.https://github.com/.extraheader
2026-03-20T09:29:24.9763977Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'http\.https\:\/\/github\.com\/\.extraheader' && git config --local --unset-all 'http.https://github.com/.extraheader' || :"
2026-03-20T09:29:24.9996984Z [command]/usr/bin/git config --local --name-only --get-regexp ^includeIf\.gitdir:
2026-03-20T09:29:25.0027958Z [command]/usr/bin/git submodule foreach --recursive git config --local --show-origin --name-only --get-regexp remote.origin.url
2026-03-20T09:29:25.0388190Z Cleaning up orphan processes
2026-03-20T09:29:25.0666955Z ##[warning]Node.js 20 actions are deprecated. The following actions are running on Node.js 20 and may not work as expected: actions/cache@v4, actions/checkout@v4, actions/setup-python@v5. Actions will be forced to run with Node.js 24 by default starting June 2nd, 2026. Please check if updated versions of these actions are available that support Node.js 24. To opt into Node.js 24 now, set the FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true environment variable on the runner or in your workflow file. Once Node.js 24 becomes the default, you can temporarily opt out by setting ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION=true. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
