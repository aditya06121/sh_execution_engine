
docker_create_python_image= docker build -t python-sandbox:latest -f docker/python.Dockerfile .

docker_create_cpp_image = docker build -t cpp-sandbox:latest -f docker/cpp.Dockerfile .

docker_create_image_command= docker build -t judge-api .

docker_run_command=
docker run \
  -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/sandbox:/sandbox \
  -e HOST_SANDBOX_ROOT=$(pwd)/sandbox \
  --name judge-api \
  judge-api

