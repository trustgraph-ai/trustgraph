
To do a public release you need to...

- Get the git directory ready for the release

- Tag the repo e.g.

```
    git tag -a v1.2.3 -m ''
    git push --tags
```

- Generate the deploy templates, don't add the `v` to the version number.

```
    templates/generate-all deploy.zip 1.2.3
```

- Release

  - Go to github, on Code tab, select tags, and find the right version
  - Select create release
  - Select the right previous version and generate release notes
  - At the bottom of the form, find the upload pad, click that and add the
    deploy.zip created earlier

- Create Python packages.   You need a PyPi token with access to our repos

  - make packages
  - make pypi-upload

- Create containers.   You need a docker hub token with acccess to our repos

  - make
  - make push

To do a local build, you need to...

- Consider what version you want to build at, and change this in Makefile.
  It doesn't really matter so long as there isn't a clash with what's in
  the public repos.  You could stick with the version that's there, or
  change to 0.0.0 if you're paranoid about pushing something accidentally.

- If you changed the version to generate templates with your version, or
  changed deployment templates, you need to recreate launch assets to
  a deploy.zip file:

```
    templates/generate-all deploy.zip V.V.V
```

- Build containers

```
    make
```


- If you changed anything which affects command line stuff (which maybe
  you could do if you changed schemas), then

```
    make packages
```

  That puts Python packages in dist/  You then need to install some or
  all of those packages.  Typically you only need -base and -cli to
  an appropriate environment e.g. use Python `venv` to create a virtual
  environment and install them there.



