#!/bin/bash
docker-compose -p smdb_test -f docker-compose.test.yml run --rm test
