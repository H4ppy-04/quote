import os
import sys

[
    sys.path.append(os.path.join(os.getcwd(), i))
    for i in [".", "tests", os.path.join("tests"), "src"]
]
