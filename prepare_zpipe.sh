#!/bin/bash

cd "$(dirname "$0")"
hg clone https://bitbucket.org/ikdc/zpipe
cd zpipe
make
