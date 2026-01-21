#!/bin/bash

BASE="http://localhost:8080"

for i in {1..200}
do
  curl -s "$BASE/rest/products" > /dev/null
  curl -s "$BASE/rest/products/search?q=test$i" > /dev/null
  curl -s "$BASE/rest/products/$((RANDOM%20+1))/reviews" > /dev/null
  curl -s "$BASE/rest/languages" > /dev/null
  sleep 0.05
done
