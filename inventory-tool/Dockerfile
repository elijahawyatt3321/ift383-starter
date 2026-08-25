FROM docker.io/library/python:3.13.13-slim@sha256:aa938a849bcb82dce8f49480f056ab82bf5c1c3ebc294f0430f37b6820e7f286

WORKDIR /app

# Seeded path defect: the Lab 7 build context is inventory-tool/ itself.
COPY inventory-tool/inventory.py ./inventory.py
COPY inventory-tool/inventory_tool ./inventory_tool

USER 65532:65532
ENTRYPOINT ["python3", "/app/inventory.py"]
