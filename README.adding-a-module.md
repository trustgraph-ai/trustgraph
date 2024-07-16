
# Contributing

## Generally

Branching is good discipline to get into with multiple people working
on the same repo for different reasons.

To create a branch...

- `git checkout -b etl` # to create the branch and check it out
- `git push` # to push the branch head to the upstream repo.  You get an error and a command to run.  You don't have to do this straight away, but I like to get the BS admin out the way.  At this stage your branch HEAD points to the head of main.

## Adding a new module

So, to add a new module...

- It needs a name. Say `kg-mymodule` but you can call it what you like.
- It also needs a place in the Python package hierarchy, because it's
  basically going to be its own loadable module.  We have a `trustgraph.kg`
  module it can be a child of.  So, you need a directory
  `trustgraph/kg/mymodule`
- You need three files:
  - `__init__.py` which defines the module entry point.
  - Then, `__main__.py` means the module is executable.
  - Finally a module to contain the code, let's call it `extract.py`.
    The name doesn't matter but it has to match what's in `__init__.py` and
    `__main__.py`.
- The easiest way to get start is maybe make a copy of an existing module.
- `cp -r trustgraph/kg/extract_relationships trustgraph/kg/mymodule/`
- Finally you need a script entry point, in `scripts`.  Copy
  `scripts/kg-extract-relationships` to `scripts/kg-mymodule`
- In that `kg-mymodule` file, change the import line to import your module,
  `trustgraph.kg.mymodule`.

## Development testing

To run your module, you don't need to have it running in a container.
It can connect to Pulsar.

The plumbing for your new module pretty needs to be right.  Look at the
input_queue, output_queue and subscriber settings near the top of your
new module code.

So, before changing the code any more, if you copied an existing module,
check the plumbing works with your renamed module.

To run standalone, it is recommended to take an existing docker-compose
file, run everything you need except the module you're developing.

Then when you launch with docker compose, you'll get everything running
except your module.

To run your module, you need to set up the Python environment as you did
in the quickstart e.g. run `. env/bin/activate` and `export PYTHONPATH=.`

You're not running kg-mymodule in a container, so it can't use docker
internal DNS to get to the containers, but the docker compose file
exposes everything to the host anyway.  You should be able to access Pulsar
on localhost port 6650, for instance.

You should be able to run your module on the host and point at Pulsar thus:

```bash
scripts/kg-mymodule -p pulsar://localhost:6650
```

You could try loading data, and check some stuff ends up in the graph.  If you get that far you're ready to hack the contents of extract.py to
do what you want.

## Structure of the code

The Processor class, `run` method is where all the fun takes place.

```
        while True:
            msg = self.consumer.receive()
```

That bit :point_up: is a loop which is executed every time a new message
arrives.

