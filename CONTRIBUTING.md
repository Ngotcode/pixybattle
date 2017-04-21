# Contributing

One of python's greatest strengths is its community's adherence to code standards guidelines - with a small team and a rapid development cycle, this will make it much easier for us to understand, explore and use each others' code. Academics are notoriously bad at it.

Some very minor things we probably all ought to be doing anyway include:

### 1. [Branches](https://help.github.com/articles/about-branches/) and [pull requests](https://help.github.com/articles/about-pull-requests/)

tl;dr smarter people than me have decided this is the best way to work in parallel

Up to you whether you want to do feature branches etc. in your own time, but we should at least avoid doing development on master (the authoritative, main 'trunk' of the code) unless it's a clear, quick fix - that'll save merge hell if there are any clashes.

Some sort of git [commit message](https://robots.thoughtbot.com/5-useful-tips-for-a-better-commit-message) would be nice - if you make interim commits too small to be worth messages, it's very easy to squash them down into one meaningful commit with `git rebase -i <after_this>` - for example, to look at the last X commits would be `git rebase -i HEAD~X`, then replace 'pick' with 'squash' (or 's') on any line you want to be squashed into the previous.

Check out a new branch with `git checkout -b <branch_name>`. If you've forgotten to do that after making some changes, `git stash` them and `git stash apply` the changes onto the new branch.

Before pushing code, and `git fetch <repo_name> master:master` and `git rebase master` so that merge conflicts happen on your local machine rather than on the remote. I recommend [meld](http://meldmerge.org/) for 3-way merges.

Merges into master should be done with a pull request on github so that there's a clear, atomic record of your changes and other people can glance at what you've changed (I doubt we'll go as far as proper reviews but at least things won't be changing underneath our feet). Feel free to [merge](https://help.github.com/articles/merging-a-pull-request/) your own PR before it gets stale.

### 2. Code standards

tl;dr uniformity and readability is valuable

[PEP20](https://www.python.org/dev/peps/pep-0020/) above all, and [PEP8](https://www.python.org/dev/peps/pep-0008/) where sensible. The exact minutiae of any given standard don't matter nearly as much as consistency, and if we need to a pick standard, why not go for the default.

### 3. [Docstrings](https://www.python.org/dev/peps/pep-0257/#what-is-a-docstring)

tl;dr document as you go along and we can save a lot of hassle

Sensible editors/ IDEs ([PyCharm](https://www.jetbrains.com/pycharm/)) and shells / REPLs ([IPython](https://ipython.org/)) allow interrogating of function and class docstrings very easily - with multiple developers, the more we can do to get the gist of each others' code without needing to go into the implementation, the better. My personal preference for docstring formatting is [NumPyDoc](https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt), which a sensible IDE ([PyCharm](https://www.jetbrains.com/pycharm/)) will stub out for you as soon as you type your triple double quotes. Next to no effort given the correct tooling, highly readable both in plaintext and in tools.

As well as making code introspection easier for humans, well-formed docstrings improve your IDE's type hinting, if it's sensible ([PyCharm](https://www.jetbrains.com/pycharm/)).

#### tl;dr whether or not the code works, shoot for style points
