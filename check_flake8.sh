#!/bin/bash
cat build/flake8.log | sort | uniq > build/flake8_final.log
diff build/flake8_final.log known_flake8.log
