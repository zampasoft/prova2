import os
from os.path import join, getsize
for root, dirs, files in os.walk('/home/nemofox/Desktop'):
    print(root, "consumes", end=" ")
    print(sum(getsize(join(root, name)) for name in files), end=" ")
    print("bytes in", len(files), "non-directory files")