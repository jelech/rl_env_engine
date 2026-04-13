# Python trainer image with PyTorch + CUDA runtime

FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime

WORKDIR /app

RUN pip install --no-cache-dir grpcio protobuf gymnasium numpy requests redis boto3

COPY python/ ./python/
RUN pip install --no-cache-dir -e ./python/

COPY api/ ./api/

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m"]
CMD ["rl_env_engine.learner"]
