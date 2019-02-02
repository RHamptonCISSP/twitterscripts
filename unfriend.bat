echo off
for /l %%x in (1, 1, 40) do (
   python unfriend.py
   echo on
   echo "loop number %%x"
   echo off
)
