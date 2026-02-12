docker run \
  -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/sandbox:/sandbox \
  -e HOST_SANDBOX_ROOT=$(pwd)/sandbox \
  judge-api
