
To do a public release you need to...

- Get the git directory ready for the release

- Tag the repo
    git tag -a v1.2.3 -m ''
    git push --tags

- Generate the deploy templates

    templates/generate-all deploy.zip 1.2.3

  (Creates a deploy.zip file)  Don't add 'v' to the version number

- Release

  - Go to github, on Code tab, select tags, and find the right version
  - Select create release
  - Select the right previous version and generate release notes
  - At the bottom of the form, find the upload pad, click that and add the
    deploy.zip created earlier

- Create Python packages

  - make packages
  - make pypi-upload

  You need a PyPi token with access to our repos

- Create containers

  - make
  - make push

  You need a docker hub token with acccess to our repos

To do a local build, you need to...

- Consider what version you want to build at, and change this in Makefile.
  It doesn't really matter so long as there isn't a clash with what's in
  the public repos.  You could stick with the version that's there, or
  change to 0.0.0 if you're paranoid about pushing something accidentally.

- If you changed the version to generate templates with your version

    templates/generate-all deploy.zip V.V.V

- make

  That builds containers.

- If you changed anything which affects command line stuff (which maybe
  you could do if you changed schemas), then

  make packages

  That puts Python packages in dist/  You then need to install some or
  all of those packages.  Typically you only need -base and -cli to
  an appropriate environment e.g. use Python `venv` to create a virtual
  environment and install them there.



