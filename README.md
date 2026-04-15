# Stillib 1.1.0

This collection of libraries provides utilities for scientific computation in python. 

## Why does this exist 

Many scientific tasks are repetitive and can be separated into (1) project specific context and (2) underlying plumbing around that context. These libraries aim to provide a centralized management of such underlying concepts that reduce boiler plate code and tries to implement a ubiquitous pattern once and well, rather than always re-writing them and making the same subtle mistakes. 


## Libraries 

- [stillib-random](libs/random/): Managed RNGs with deterministic spawning, multiprocessing and store/resume support.

- [stillib-montecarlo](libs/montecarlo/): Simulated propagation of stochastic variables such as error propagation.

- [stillib-parallelism](libs/parallelism/): Process Pool distribution of embarrasigly parallel (independent) tasks.

- [stillib-paths](libs/paths/): Utilites for structured path objects with better ergonomics

- [stillib-plotting](libs/plotting/): Matplotlib based standardization of style, plot sizes, save fig behavior, etc.

## Installation

From Stillib project root, install a particular library into your current environment using:
```bash 
python installer.py <library name>
```

To install all libraries, run:
```bash 
python installer.py all
```

### [LICENSE](LICENSE) 