# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""저장소 어느 위치에서 pytest 를 불러도 camera_manager 를 import 할 수 있게 한다."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
