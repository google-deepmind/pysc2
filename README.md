pip install --upgrade --target pip/ enum34 futures google-apputils numpy \
  portpicker protobuf python-gflags pygame websocket-client && \
  touch pip/google/protobuf/__init__.py pip/google/__init__.py

~/src/protobuf/src/protoc --proto_path . --python_out . s2clientproto/common.proto && \
~/src/protobuf/src/protoc --proto_path . --python_out . s2clientproto/data.proto && \
~/src/protobuf/src/protoc --proto_path . --python_out . s2clientproto/debug.proto && \
~/src/protobuf/src/protoc --proto_path . --python_out . s2clientproto/error.proto && \
~/src/protobuf/src/protoc --proto_path . --python_out . s2clientproto/query.proto && \
~/src/protobuf/src/protoc --proto_path . --python_out . s2clientproto/raw.proto && \
~/src/protobuf/src/protoc --proto_path . --python_out . s2clientproto/sc2api.proto && \
~/src/protobuf/src/protoc --proto_path . --python_out . s2clientproto/score.proto && \
~/src/protobuf/src/protoc --proto_path . --python_out . s2clientproto/spatial.proto && \
~/src/protobuf/src/protoc --proto_path . --python_out . s2clientproto/ui.proto

PYTHONPATH=.:$PWD/pip pysc2/bin/sc_client.py --map Overgrowth
